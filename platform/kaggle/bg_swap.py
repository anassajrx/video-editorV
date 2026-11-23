"""Background swap on the Kaggle T4: the tested Colab cells B1-B5 (video_prep_and_background.ipynb) as one function.

swap(src, background_image, out_dir, has_me=True, progress=cb, **realism) -> (out_video, compare_video)
  1. background: fit to the video; if you're in the image, BiRefNet finds you and LaMa fills the hole
  2. cut-out: MatAnyone 2 follows you frame by frame (first-frame mask from BiRefNet)       <- real frame progress
  3. composite: your edges cleaned with your real room plate, colour match, light wrap, grain <- real frame progress
progress(step, done, total, unit) is called with real counts (frames).
"""
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

MA2_COMMIT = "0079197acd6d16a741f71558809c06c586c579e0"  # the version the notebook was tested with
SEG_MODEL = "birefnet-portrait"
READ_VF = "scale=in_color_matrix=bt709:in_range=tv"
WRITE_VF = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
TAGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]
_PM_SCRIPT = """
import sys, numpy as np
from PIL import Image
from rembg import new_session, remove
s = new_session(sys.argv[3])
m = remove(Image.open(sys.argv[1]).convert("RGB"), session=s, only_mask=True)
np.save(sys.argv[2], np.array(m.convert("L")))
"""


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], flush=True)
        raise RuntimeError("Command failed: " + " ".join(map(str, cmd[:8])) + " ...")
    return r.stdout


def setup(work):
    ma2 = Path(work) / "MatAnyone2"
    if not ma2.exists():
        run(["git", "clone", "-q", "https://github.com/pq-yang/MatAnyone2", str(ma2)])
        run(["git", "-C", str(ma2), "checkout", "-q", MA2_COMMIT])
    sys.path.insert(0, str(ma2))
    # MatAnyone 2's own package install is broken with new build tools: use its code + only the missing packages
    run([sys.executable, "-m", "pip", "-q", "install", "hydra-core", "omegaconf", "onnxruntime", "pooch", "pymatting"])
    run([sys.executable, "-m", "pip", "-q", "install", "--no-deps", "rembg", "simple-lama-inpainting"])


def swap(src, background_image, out_dir, has_me=True, progress=None, matting_size=1080, color_match=0.25,
         light_wrap=0.35, background_blur=1.5, grain=1.0, edge_tighten=0.0, work="/kaggle/working/swap"):
    prog = progress or (lambda *a, **k: None)
    WORK = Path(work)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT = Path(out_dir)
    OUT.mkdir(parents=True, exist_ok=True)
    prog("bg_setup", 0, 3, "steps")
    setup(work)
    prog("bg_setup", 1, 3, "steps")
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    DEV = torch.device("cuda")

    def probe(path):
        j = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,avg_frame_rate,r_frame_rate:"
                            "format=duration", "-of", "json", str(path)]))
        v = next(s for s in j["streams"] if s["codec_type"] == "video")
        num, den = ((v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1").split("/") + ["1"])[:2]
        fps = float(num) / float(den) if float(den) else 30.0
        return dict(w=int(v["width"]), h=int(v["height"]), fps=fps, dur=float(j["format"].get("duration", 0)),
                    audio=any(s["codec_type"] == "audio" for s in j["streams"]))

    def read_frames(path, w, h, gray=False):
        ch = 1 if gray else 3
        cmd = ["ffmpeg", "-v", "error", "-i", str(path)] + ([] if gray else ["-vf", READ_VF])
        cmd += ["-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24", "-"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=w * h * ch * 4)
        n = w * h * ch
        try:
            while True:
                b = p.stdout.read(n)
                if len(b) < n:
                    break
                yield np.frombuffer(b, np.uint8).reshape(h, w, ch)
        finally:
            p.stdout.close()
            p.wait()

    def writer(path, w, h, fps, gray=False, audio_from=None):
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24",
               "-s", f"{w}x{h}", "-r", f"{fps:.6f}", "-i", "-"]
        if gray:
            cmd += ["-c:v", "ffv1", str(path)]
        else:
            if audio_from:
                cmd += ["-i", str(audio_from), "-map", "0:v", "-map", "1:a?", "-c:a", "aac", "-b:a", "192k", "-shortest"]
            cmd += ["-vf", WRITE_VF, *X264, *TAGS, "-movflags", "+faststart", str(path)]
        return subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def gblur(x, sigma):
        if sigma <= 0.05:
            return x
        r = max(1, int(math.ceil(sigma * 3)))
        k = torch.arange(-r, r + 1, device=x.device, dtype=x.dtype)
        k = torch.exp(-(k * k) / (2 * sigma * sigma))
        k = k / k.sum()
        c = x.shape[0]
        y = F.pad(x[None], (r, r, 0, 0), mode="replicate")
        y = F.conv2d(y, k.view(1, 1, 1, -1).repeat(c, 1, 1, 1), groups=c)
        y = F.pad(y, (0, 0, r, r), mode="replicate")
        y = F.conv2d(y, k.view(1, 1, -1, 1).repeat(c, 1, 1, 1), groups=c)
        return y[0]

    def big_blur(x, sigma):
        if sigma < 6:
            return gblur(x, sigma)
        h, w = x.shape[-2:]
        s = F.interpolate(x[None], scale_factor=0.25, mode="area")[0]
        s = gblur(s, sigma / 4)
        return F.interpolate(s[None], size=(h, w), mode="bilinear", align_corners=False)[0]

    def person_mask(img_rgb):
        """BiRefNet-portrait through rembg, in its own process (peaks at ~9.5 GB RAM, freed on exit)."""
        pth, outp, scr = WORK / "_pm_in.png", WORK / "_pm_out.npy", WORK / "_pm.py"
        scr.write_text(_PM_SCRIPT)
        Image.fromarray(img_rgb).save(pth)
        r = subprocess.run([sys.executable, str(scr), str(pth), str(outp), SEG_MODEL], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-2000:], flush=True)
            raise RuntimeError("The person-finder (BiRefNet) failed.")
        m = np.load(outp)
        return np.array(Image.fromarray(m).resize((img_rgb.shape[1], img_rgb.shape[0]), Image.BILINEAR))

    # ---- B3: the video, BT.709-tagged, long side max 1920 ----
    info = probe(src)
    fps = info["fps"] if 1 < info["fps"] <= 120 else 30.0
    fps = round(fps * 1000) / 1000
    segment = WORK / "segment.mp4"
    vf = ["scale='if(gt(iw,ih),min(1920,iw),-2)':'if(gt(iw,ih),-2,min(1920,ih))':flags=lanczos",
          "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"]
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", ",".join(vf), "-vsync", "cfr", "-r", f"{fps}", *X264, *TAGS,
         "-c:a", "aac", "-b:a", "192k", str(segment)])
    seg = probe(segment)
    W, H, FPS = seg["w"], seg["h"], seg["fps"]
    N = int(round(seg["dur"] * FPS))
    frame0 = next(read_frames(segment, W, H))
    prog("bg_setup", 2, 3, "steps")

    # ---- B4: the background ----
    bg = Image.open(background_image).convert("RGB")
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((math.ceil(bg.width * scale), math.ceil(bg.height * scale)), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = np.array(bg.crop((left, top, left + W, top + H)))
    if has_me:
        import cv2
        pm = person_mask(bg) > 40
        k = max(9, int(0.03 * min(W, H)) | 1)
        hole = cv2.dilate(pm.astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        f = min(1.0, 1280 / max(W, H))
        sw, sh_ = int(W * f) // 8 * 8, int(H * f) // 8 * 8
        from simple_lama_inpainting import SimpleLama
        lama = SimpleLama()
        filled = lama(Image.fromarray(bg).resize((sw, sh_), Image.LANCZOS), Image.fromarray(hole).resize((sw, sh_), Image.NEAREST))
        filled = np.array(filled.crop((0, 0, sw, sh_)).resize((W, H), Image.LANCZOS)).astype(np.float32)
        soft = cv2.GaussianBlur(hole, (0, 0), k / 6).astype(np.float32)[..., None] / 255
        bg = (bg * (1 - soft) + filled * soft).clip(0, 255).astype(np.uint8)
        del lama
        torch.cuda.empty_cache()
    BG_CLEAN = OUT / "background_clean.png"
    Image.fromarray(bg).save(BG_CLEAN)
    prog("bg_setup", 3, 3, "steps")

    # ---- B4b: cut-out with MatAnyone 2 ----
    from matanyone2 import InferenceCore, MatAnyone2
    from matanyone2.utils.inference_utils import gen_dilate, gen_erosion
    m0 = person_mask(frame0)
    first_mask = ((m0 > 127) * 255).astype(np.uint8)
    if first_mask.mean() <= 2:
        raise RuntimeError("No person found in the first frame of the video.")
    model = MatAnyone2.from_pretrained("PeiqingYang/MatAnyone2")
    proc = InferenceCore(model, device=DEV)
    N_WARMUP = 10
    short = min(W, H)
    nh, nw = (int(H / short * matting_size), int(W / short * matting_size)) if short > matting_size else (H, W)
    mask = gen_erosion(gen_dilate(first_mask, 10, 10), 10, 10)
    mask_t = torch.from_numpy(mask).float().to(DEV)
    if (nh, nw) != (H, W):
        mask_t = F.interpolate(mask_t[None, None], size=(nh, nw), mode="nearest")[0, 0]
    ALPHA = WORK / "alpha.mkv"
    aw = writer(ALPHA, W, H, FPS, gray=True)
    plate_sum = torch.zeros(3, H, W, device=DEV)
    plate_cnt = torch.zeros(1, H, W, device=DEV)

    def frames_with_warmup():
        for _ in range(N_WARMUP):
            yield frame0
        yield from read_frames(segment, W, H)

    done = 0
    prog("cutout", 0, N, "frames")
    with torch.inference_mode(), torch.amp.autocast(device_type="cuda"):
        for ti, fr in enumerate(frames_with_warmup()):
            full = torch.from_numpy(fr.copy()).to(DEV).permute(2, 0, 1).float()
            img = full if (nh, nw) == (H, W) else F.interpolate(full[None], size=(nh, nw), mode="area")[0]
            img = img / 255.0
            if ti == 0:
                proc.step(img, mask_t, objects=[1])
                prob = proc.step(img, first_frame_pred=True)
            elif ti <= N_WARMUP:
                prob = proc.step(img, first_frame_pred=True)
            else:
                prob = proc.step(img)
            if ti < N_WARMUP:
                continue
            a = proc.output_prob_to_mask(prob).float().clamp(0, 1)
            if a.shape[-2:] != (H, W):
                a = F.interpolate(a[None, None], size=(H, W), mode="bilinear", align_corners=False)[0, 0]
            a = a[None]
            bgm = (a < 0.02).float()
            plate_sum += full / 255.0 * bgm
            plate_cnt += bgm
            aw.stdin.write((a[0] * 255 + 0.5).byte().cpu().numpy().tobytes())
            done += 1
            if done % 15 == 0:
                prog("cutout", done, N, "frames")
    aw.stdin.close()
    aw.wait()
    prog("cutout", N, N, "frames")
    del model, proc
    torch.cuda.empty_cache()

    # ---- B5: composite ----
    out_path = OUT / "edit_swapped.mp4"
    prog("composite", 0, N, "frames")
    with torch.inference_mode():
        Bn = torch.from_numpy(np.array(Image.open(BG_CLEAN).convert("RGB"))).to(DEV).permute(2, 0, 1).float() / 255
        Bn = gblur(Bn, background_blur * H / 1920)
        px = max(W, H) / 1920
        Bwrap = big_blur(Bn, 14 * px)
        cnt = plate_cnt
        plate = plate_sum / cnt.clamp(min=1)
        valid = (cnt >= 3).float()
        fill_s = 40 * px
        filled = big_blur(plate * valid, fill_s) / big_blur(valid, fill_s).clamp(min=1e-3)
        plate = plate * valid + filled * (1 - valid)
        valid_soft = big_blur(valid, 3 * px)

        def to_ycc(x):
            y = 0.2126 * x[0] + 0.7152 * x[1] + 0.0722 * x[2]
            return torch.stack([y, (x[2] - y) / 1.8556, (x[0] - y) / 1.5748])

        def from_ycc(c):
            y, cb, cr = c
            r = y + 1.5748 * cr
            b = y + 1.8556 * cb
            g = (y - 0.2126 * r - 0.0722 * b) / 0.7152
            return torch.stack([r, g, b])

        def foreground(I, a):
            solved = (I - (1 - a) * plate) / a.clamp(min=0.05)
            spread = gblur(I * a, 4 * px) / gblur(a, 4 * px).clamp(min=1e-4)
            w = ((a - 0.15) / 0.35).clamp(0, 1) * valid_soft
            Fg = w * solved + (1 - w) * spread
            Fg = torch.where(a > 0.97, I, Fg)
            return Fg.clamp(0, 1)

        a0 = next(read_frames(ALPHA, W, H, gray=True))
        a0 = torch.from_numpy(a0.copy()).to(DEV).permute(2, 0, 1).float() / 255
        I0 = torch.from_numpy(frame0.copy()).to(DEV).permute(2, 0, 1).float() / 255
        fg_px = to_ycc(foreground(I0, a0))[:, a0[0] > 0.95]
        bg_ycc = to_ycc(Bn).flatten(1)
        if fg_px.shape[1] < 100:
            fg_px = to_ycc(I0).flatten(1)
        shift = (bg_ycc.mean(1) - fg_px.mean(1)) * color_match
        shift[0] *= 0.5
        shift = shift.view(3, 1, 1)
        hp = (I0 - gblur(I0, 1.0)).mean(0)
        bgpix = hp[(a0[0] < 0.02)]
        noise = float(1.4826 * bgpix.abs().median()) if bgpix.numel() > 1000 else 0.01
        noise = min(noise, 0.05) * grain
        vw = writer(out_path, W, H, FPS, audio_from=segment if seg["audio"] else None)
        n = 0
        for fr, af in zip(read_frames(segment, W, H), read_frames(ALPHA, W, H, gray=True)):
            I = torch.from_numpy(fr.copy()).to(DEV).permute(2, 0, 1).float() / 255
            a = torch.from_numpy(af.copy()).to(DEV).permute(2, 0, 1).float() / 255
            if edge_tighten > 0:
                a = ((a - edge_tighten) / (1 - edge_tighten)).clamp(0, 1)
            Fg = foreground(I, a)
            if color_match > 0:
                Fg = from_ycc(to_ycc(Fg) + shift).clamp(0, 1)
            bgf = (Bn + torch.randn(1, H, W, device=DEV) * noise).clamp(0, 1) if noise > 0 else Bn
            comp = a * Fg + (1 - a) * bgf
            if light_wrap > 0:
                wrap = (big_blur(1 - a, 10 * px) * a * light_wrap).clamp(0, 1)
                comp = comp * (1 - wrap) + Bwrap * wrap
            vw.stdin.write((comp.clamp(0, 1) * 255 + 0.5).byte().permute(1, 2, 0).contiguous().cpu().numpy().tobytes())
            n += 1
            if n % 15 == 0:
                prog("composite", n, N, "frames")
        vw.stdin.close()
        vw.wait()
    prog("composite", N, N, "frames")
    compare = OUT / "compare-background.mp4"
    ch = min(H, 960) // 2 * 2
    run(["ffmpeg", "-v", "error", "-y", "-i", str(segment), "-i", str(out_path), "-filter_complex",
         f"[0:v]scale=-2:{ch}[a];[1:v]scale=-2:{ch}[b];[a][b]hstack[v]", "-map", "[v]", "-map", "0:a?",
         *X264, "-c:a", "aac", "-shortest", str(compare)])
    return out_path, compare
