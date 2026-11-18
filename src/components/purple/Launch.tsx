import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, purple } from "../../brand/theme";
import { camAt, easeIO, outBack, type ShotKey } from "./Moments";

/**
 * "SaaS launch" finale: ONE continuous full-screen scene (no footage between beats, so no glimpse of the face),
 * built from the real platform screens. Beats (seconds from the overlay start) are props so another video can
 * re-time them to its own voice:
 *   head      kinetic headline ("Don't trust words. / See it yourself.")
 *   browser   browser window flies in on the platform screen, camera to the course card, cursor clicks "Commencer"
 *   lesson    the lesson page slides in, cursor clicks play
 *   form      a sign-up form types itself, "below the video" pointer, Send -> sent
 *   chat      a data pulse travels to a phone, the advisor's messages arrive on WhatsApp
 *   finale    flash + shockwave + rays, logo, wordmark, url pill with a shine, "Start today" button
 */
export type LaunchBeats = {
  browser: number; zoom: number; click: number; lesson: number; play: number;
  form: number; arrow: number; send: number; chat: number; msg1: number; msg2: number; reply: number; finale: number;
};
const DEFAULT_BEATS: LaunchBeats = {
  browser: 1.3, zoom: 2.0, click: 3.35, lesson: 3.55, play: 4.5,
  form: 5.05, arrow: 5.75, send: 6.75, chat: 7.0, msg1: 7.7, msg2: 8.75, reply: 9.3, finale: 9.8,
};

const cl = (x: number) => Math.max(0, Math.min(1, x));
const seg = (t: number, a: number, b: number) => cl((t - a) / Math.max(0.001, b - a));
const rnd = (i: number) => { const x = Math.sin(i * 12.9898 + 78.233) * 43758.5453; return x - Math.floor(x); };

/** The arrow cursor + click ripple, drawn in the coordinates of whatever it sits in. */
const Cursor: React.FC<{ x: number; y: number; t: number; clickAt: number; size: number; opacity?: number }> = ({ x, y, t, clickAt, size, opacity = 1 }) => {
  const r = cl((t - clickAt) / 0.55);
  const press = t >= clickAt && t < clickAt + 0.15 ? 0.82 : 1;
  return (
    <>
      {t >= clickAt && r < 1 ? (
        <div style={{ position: "absolute", left: x, top: y, width: size * 3, height: size * 3, borderRadius: "50%",
          transform: `translate(-50%, -50%) scale(${0.2 + r})`, border: `${size * 0.11}px solid ${purple.violet}`,
          background: "rgba(139,92,246,.18)", opacity: 1 - r }} />
      ) : null}
      <svg width={size} height={size} viewBox="0 0 24 24" style={{ position: "absolute", left: x - size * 0.13, top: y - size * 0.09,
        opacity, transform: `scale(${press})`, transformOrigin: "20% 15%", filter: `drop-shadow(0 ${size * 0.08}px ${size * 0.12}px rgba(0,0,0,.45))` }}>
        <path d="M4 2 L4 20 L9 15.5 L12.5 22.5 L15.5 21 L12 14 L19 14 Z" fill="#111" stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
      </svg>
    </>
  );
};

/** A screenshot with a keyframed camera; `children(cw, ch, z)` draws in image coordinates (moves with it). */
const ShotView: React.FC<{ w: number; h: number; src: string; keys: ShotKey[]; t: number;
  children?: (cw: number, ch: number, z: number) => React.ReactNode }> = ({ w, h, src, keys, t, children }) => {
  const cam = camAt(keys, t);
  const z = Math.max(1, cam.zoom);
  const tx = Math.min(0, Math.max(w - z * w, w / 2 - z * cam.fx * w));
  const ty = Math.min(0, Math.max(h - z * h, h / 2 - z * cam.fy * h));
  return (
    <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${z})` }}>
        <Img src={staticFile(src)} style={{ width: w, height: h, display: "block" }} />
        {children ? children(w, h, z) : null}
      </div>
    </div>
  );
};

export const LaunchSequence: React.FC<{
  durationInFrames: number;
  platform: string; // the "Mes cours" screen (16:9)
  lesson: string; // the lesson page (16:9)
  logo: string; // white logo (png with alpha)
  brand?: string;
  url?: string;
  cta?: string;
  headline?: [string, string];
  beats?: Partial<LaunchBeats>;
}> = ({ durationInFrames, platform, lesson, logo, brand = "Progma Academy", url = "progma.ai", cta = "Start today",
  headline = ["Don't trust words.", "See it yourself."], beats }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const s = Math.min(W, H) / 1080;
  const t = frame / fps;
  const D = durationInFrames / fps;
  const b = { ...DEFAULT_BEATS, ...beats };
  const fin = seg(t, b.finale, b.finale + 0.5); // scenes zoom through into the finale

  // ---------- background: plum, drifting orbs, moving neon grid floor, rising particles ----------
  const bgIn = seg(t, 0, 0.3);
  const orb = (cx: number, cy: number, r: number, c: string, ph: number) => (
    <div style={{ position: "absolute", left: (cx + 0.05 * Math.sin(t * 0.7 + ph)) * W - r, top: (cy + 0.05 * Math.cos(t * 0.5 + ph)) * H - r,
      width: 2 * r, height: 2 * r, borderRadius: "50%", background: `radial-gradient(circle, ${c} 0%, transparent 65%)`, filter: `blur(${30 * s}px)` }} />
  );
  const background = (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 70% at 50% 45%, #2A1A4A 0%, #120A1F 70%, #0B0614 100%)`, opacity: bgIn }}>
      {orb(0.22, 0.3, 520 * s, "rgba(139,92,246,.45)", 0)}
      {orb(0.8, 0.65, 600 * s, "rgba(91,33,182,.5)", 2)}
      {orb(0.55, 0.15, 380 * s, "rgba(196,181,253,.18)", 4)}
      <div style={{ position: "absolute", left: -W, width: 3 * W, bottom: -0.05 * H, height: 0.6 * H, transformOrigin: "50% 100%",
        transform: `perspective(${700 * s}px) rotateX(72deg)`,
        backgroundImage: `linear-gradient(rgba(167,139,250,.45) ${2 * s}px, transparent ${2 * s}px), linear-gradient(90deg, rgba(167,139,250,.45) ${2 * s}px, transparent ${2 * s}px)`,
        backgroundSize: `${90 * s}px ${90 * s}px`, backgroundPosition: `0 ${(t * 70 * s) % (90 * s)}px`,
        WebkitMaskImage: "linear-gradient(to top, rgba(0,0,0,.9), transparent 85%)", maskImage: "linear-gradient(to top, rgba(0,0,0,.9), transparent 85%)" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 0.62 * H, height: 2 * s, background: "linear-gradient(90deg, transparent, rgba(196,181,253,.7), transparent)",
        boxShadow: `0 0 ${30 * s}px rgba(139,92,246,.8)`, opacity: 0.6 }} />
      {Array.from({ length: 46 }).map((_, i) => {
        const x = rnd(i) * W, sp = 0.03 + rnd(i + 99) * 0.07, y = ((1.1 - ((t * sp + rnd(i + 7)) % 1.2)) * H), r = (1.5 + rnd(i + 3) * 3) * s;
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: r * 2, height: r * 2, borderRadius: "50%",
          background: purple.lilac, opacity: 0.25 + 0.5 * rnd(i + 5), boxShadow: `0 0 ${8 * s}px ${purple.violet}` }} />;
      })}
    </AbsoluteFill>
  );

  // ---------- 1. headline ----------
  const headOut = seg(t, b.browser - 0.15, b.browser + 0.25);
  const word = (txt: string, i: number, line: number) => {
    const a = seg(t, 0.12 + line * 0.45 + i * 0.07, 0.42 + line * 0.45 + i * 0.07);
    return (
      <span key={i} style={{ display: "inline-block", marginRight: 22 * s, opacity: a, filter: `blur(${(1 - a) * 12 * s}px)`,
        transform: `translateY(${(1 - easeIO(a)) * 40 * s}px)`,
        ...(line === 1 ? { background: `linear-gradient(90deg, ${purple.lilac}, ${purple.violet} 70%, #F0ABFC)`,
          WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent", paddingBottom: 8 * s } : {}) }}>{txt}</span>
    );
  };
  const headline1 = headOut < 1 ? (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: 1 - headOut,
      transform: `scale(${1 + headOut * 0.6})`, filter: `blur(${headOut * 10 * s}px)` }}>
      <div style={{ textAlign: "center", fontFamily: fonts.display, fontWeight: 800, letterSpacing: -2 * s, marginTop: 40 * s }}>
        <div style={{ fontSize: 96 * s, color: purple.white }}>{headline[0].split(" ").map((w, i) => word(w, i, 0))}</div>
        <div style={{ fontSize: 120 * s }}>{headline[1].split(" ").map((w, i) => word(w, i, 1))}</div>
      </div>
    </AbsoluteFill>
  ) : null;

  // ---------- 2. browser window: platform -> click Commencer -> lesson -> click play ----------
  const bIn = easeIO(seg(t, b.browser, b.browser + 0.75));
  const bOut = easeIO(seg(t, b.form - 0.15, b.form + 0.3));
  const bw = 0.64 * W, bar = 46 * s, bch = bw * 9 / 16, bh = bch + bar;
  const bx = (W - bw) / 2, by = 0.585 * H - bh / 2;
  const lessonP = easeIO(seg(t, b.lesson, b.lesson + 0.45));
  const platformKeys: ShotKey[] = [
    { t: 0, zoom: 1, fx: 0.5, fy: 0.5 }, { t: b.zoom - b.browser, zoom: 1, fx: 0.5, fy: 0.5 },
    { t: b.zoom - b.browser + 0.7, zoom: 1.75, fx: 0.31, fy: 0.42 }, { t: 9, zoom: 1.75, fx: 0.31, fy: 0.42 },
  ];
  const lessonKeys: ShotKey[] = [
    { t: 0, zoom: 1, fx: 0.5, fy: 0.5 }, { t: 0.5, zoom: 1, fx: 0.5, fy: 0.5 }, { t: 1.1, zoom: 1.45, fx: 0.55, fy: 0.45 }, { t: 9, zoom: 1.5, fx: 0.55, fy: 0.45 },
  ];
  const tb = t - b.browser;
  const cur1 = easeIO(seg(t, b.zoom + 0.6, b.click - 0.05));
  const cur2 = easeIO(seg(t, b.lesson + 0.6, b.play - 0.05));
  const freePill = outBack(seg(t, b.lesson + 0.35, b.lesson + 0.75));
  const browser = bIn > 0 && bOut < 1 ? (
    <div style={{ position: "absolute", inset: 0, perspective: 1600 * s }}>
      <div style={{ position: "absolute", left: bx, top: by, width: bw, height: bh, borderRadius: 18 * s, overflow: "hidden",
        background: "#fff", border: `${1.5 * s}px solid rgba(196,181,253,.4)`,
        boxShadow: `0 ${40 * s}px ${120 * s}px rgba(0,0,0,.6), 0 0 ${80 * s}px rgba(139,92,246,.35)`,
        opacity: Math.min(1, bIn * 1.5) * (1 - bOut),
        transform: `translateY(${(1 - bIn) * 260 * s - bOut * 300 * s}px) rotateX(${(1 - bIn) * 28 + Math.sin(t * 0.8) * 1.2}deg) rotateY(${Math.sin(t * 0.6) * 2}deg) scale(${0.85 + 0.15 * bIn - bOut * 0.1})` }}>
        <div style={{ height: bar, background: "#F1EEF8", display: "flex", alignItems: "center", padding: `0 ${18 * s}px`, gap: 9 * s, borderBottom: `${s}px solid #E4DEF2` }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 13 * s, height: 13 * s, borderRadius: "50%", background: c }} />)}
          <div style={{ marginLeft: 18 * s, flex: 1, height: 28 * s, borderRadius: 999, background: "#fff", border: `${s}px solid #E4DEF2`,
            display: "flex", alignItems: "center", paddingLeft: 16 * s, fontFamily: fonts.display, fontSize: 17 * s, color: "#5B5470" }}>
            <span style={{ color: "#22A06B", marginRight: 8 * s }}>●</span>academy.{url}
          </div>
        </div>
        <div style={{ position: "absolute", left: 0, top: bar, width: bw, height: bch, overflow: "hidden" }}>
          <div style={{ position: "absolute", inset: 0, transform: `translateX(${-lessonP * 30}%)`, filter: `brightness(${1 - 0.4 * lessonP})` }}>
            <ShotView w={bw} h={bch} src={platform} keys={platformKeys} t={tb}>
              {(cw, ch, z) => (cur1 > 0 && lessonP < 1 ? (
                <Cursor x={(0.6 + (0.318 - 0.6) * cur1) * cw} y={(0.78 + (0.593 - 0.78) * cur1) * ch} t={t} clickAt={b.click} size={(48 * s) / z} />
              ) : null)}
            </ShotView>
          </div>
          {lessonP > 0 ? (
            <div style={{ position: "absolute", inset: 0, transform: `translateX(${(1 - lessonP) * 100}%)`, boxShadow: `-${30 * s}px 0 ${60 * s}px rgba(0,0,0,.35)` }}>
              <ShotView w={bw} h={bch} src={lesson} keys={lessonKeys} t={t - b.lesson}>
                {(cw, ch, z) => {
                  const pulse = t > b.play ? 0 : 0.5 + 0.5 * Math.sin(t * 7);
                  return (
                    <>
                      <div style={{ position: "absolute", left: 0.62 * cw, top: 0.453 * ch, width: (90 + 30 * pulse) * s / z, height: (90 + 30 * pulse) * s / z,
                        transform: "translate(-50%, -50%)", borderRadius: "50%", border: `${4 * s / z}px solid ${purple.violet}`, opacity: 0.7 * (1 - pulse * 0.5) * (t < b.play + 0.3 ? 1 : 0) }} />
                      {cur2 > 0 ? <Cursor x={(0.45 + (0.62 - 0.45) * cur2) * cw} y={(0.72 + (0.453 - 0.72) * cur2) * ch} t={t} clickAt={b.play} size={(48 * s) / z} /> : null}
                    </>
                  );
                }}
              </ShotView>
            </div>
          ) : null}
          {freePill > 0 ? (
            <div style={{ position: "absolute", left: 24 * s, bottom: 24 * s, padding: `${12 * s}px ${24 * s}px`, borderRadius: 999, background: purple.violet,
              color: "#fff", fontFamily: fonts.display, fontWeight: 800, fontSize: 32 * s, transform: `scale(${freePill})`, transformOrigin: "0 100%",
              boxShadow: `0 ${10 * s}px ${30 * s}px rgba(0,0,0,.35)` }}>Lesson 1 · free</div>
          ) : null}
        </div>
      </div>
    </div>
  ) : null;

  // ---------- 3. form ----------
  const fIn = outBack(seg(t, b.form, b.form + 0.55));
  const fSide = easeIO(seg(t, b.chat - 0.1, b.chat + 0.5)); // form moves left when the phone arrives
  const fw = 0.34 * W;
  const fcx = W / 2 - fSide * 0.21 * W, fcy = 0.56 * H;
  const typed = (txt: string, a: number, bEnd: number) => txt.slice(0, Math.round(txt.length * seg(t, a, bEnd)));
  const name = typed("Yassine", b.form + 0.4, b.form + 0.85);
  const phone = typed("06 12 •• •• ••", b.form + 0.95, b.send - 0.45);
  const sent = t >= b.send + 0.1;
  const caret = Math.floor(t * 3) % 2 === 0 ? "|" : " ";
  const arrowP = outBack(seg(t, b.arrow, b.arrow + 0.4));
  const field = (label: string, value: string, active: boolean) => (
    <div style={{ marginTop: 18 * s }}>
      <div style={{ fontSize: 19 * s, color: "#6B6385", marginBottom: 8 * s, fontWeight: 600 }}>{label}</div>
      <div style={{ height: 58 * s, borderRadius: 12 * s, border: `${2 * s}px solid ${active ? purple.violet : "#E4DEF2"}`, background: "#FAF9FD",
        display: "flex", alignItems: "center", paddingLeft: 18 * s, fontSize: 26 * s, color: "#1B1530", fontWeight: 600,
        boxShadow: active ? `0 0 0 ${5 * s}px rgba(139,92,246,.15)` : "none" }}>{value}{active ? caret : ""}</div>
    </div>
  );
  const sendBtnX = fcx, sendBtnY = fcy + 0.04 * H;
  const curF = easeIO(seg(t, b.send - 0.6, b.send - 0.05));
  const form = fIn > 0 && fin < 1 ? (
    <>
      <div style={{ position: "absolute", left: fcx - fw / 2, top: fcy - 0.3 * H, width: fw, padding: `${34 * s}px ${38 * s}px`, boxSizing: "border-box",
        borderRadius: 28 * s, background: "#fff", fontFamily: fonts.display,
        boxShadow: `0 ${40 * s}px ${110 * s}px rgba(0,0,0,.55), 0 0 ${70 * s}px rgba(139,92,246,.35)`,
        transform: `scale(${fIn * (1 - 0.12 * fSide)})`, transformOrigin: "50% 50%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 * s }}>
          <div style={{ width: 46 * s, height: 46 * s, borderRadius: 12 * s, background: purple.violet, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Img src={staticFile(logo)} style={{ width: 30 * s }} />
          </div>
          <div>
            <div style={{ fontSize: 30 * s, fontWeight: 800, color: "#1B1530", letterSpacing: -0.5 * s }}>Join the training</div>
            <div style={{ fontSize: 18 * s, color: "#6B6385" }}>An advisor calls you back on WhatsApp</div>
          </div>
        </div>
        {field("Your name", name, t > b.form + 0.35 && t < b.form + 0.9)}
        {field("WhatsApp number", phone, t >= b.form + 0.9 && !sent)}
        <div style={{ marginTop: 26 * s, height: 64 * s, borderRadius: 14 * s, background: sent ? "#22C55E" : purple.violet, color: "#fff",
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26 * s, fontWeight: 800,
          transform: `scale(${t >= b.send && t < b.send + 0.15 ? 0.96 : 1})`, boxShadow: `0 ${10 * s}px ${30 * s}px ${sent ? "rgba(34,197,94,.45)" : "rgba(139,92,246,.45)"}` }}>
          {sent ? "Sent ✓" : "Send →"}
        </div>
      </div>
      {arrowP > 0 && fSide < 1 ? (
        <div style={{ position: "absolute", left: fcx + fw / 2 + 36 * s, top: fcy + 0.02 * H, transform: `scale(${arrowP})`, transformOrigin: "0 50%",
          opacity: 1 - fSide, display: "flex", flexDirection: "column", alignItems: "center", fontFamily: fonts.display }}>
          <div style={{ padding: `${12 * s}px ${22 * s}px`, borderRadius: 999, background: purple.violet, color: "#fff", fontWeight: 800, fontSize: 30 * s,
            whiteSpace: "nowrap", boxShadow: `0 0 ${30 * s}px rgba(139,92,246,.6)` }}>below the video</div>
          <svg width={70 * s} height={90 * s} viewBox="0 0 24 30" style={{ marginTop: 6 * s, transform: `translateY(${Math.abs(Math.sin(t * 6)) * 14 * s}px)` }}>
            <path d="M12 2 V26 M4 18 L12 26 L20 18" stroke={purple.lilac} strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      ) : null}
      {curF > 0 && t < b.send + 0.6 ? (
        <Cursor x={sendBtnX + (1 - curF) * 0.12 * W} y={sendBtnY + (1 - curF) * 0.1 * H} t={t} clickAt={b.send} size={48 * s} opacity={1 - seg(t, b.send + 0.3, b.send + 0.6)} />
      ) : null}
    </>
  ) : null;

  // ---------- 4. phone with the advisor's messages ----------
  const pIn = easeIO(seg(t, b.chat, b.chat + 0.6));
  const pw = 0.2 * W, ph = 0.68 * H;
  const pcx = W / 2 + 0.2 * W, pcy = 0.6 * H;
  const packet = seg(t, b.chat + 0.2, b.chat + 0.85);
  const bubble = (at: number, text: string, out = false) => {
    const a = outBack(seg(t, at, at + 0.35));
    if (a <= 0) return null;
    return (
      <div style={{ alignSelf: out ? "flex-end" : "flex-start", maxWidth: "82%", marginTop: 12 * s, padding: `${12 * s}px ${16 * s}px`,
        borderRadius: 16 * s, borderTopLeftRadius: out ? 16 * s : 4 * s, borderTopRightRadius: out ? 4 * s : 16 * s,
        background: out ? "#D9FDD3" : "#fff", color: "#111B21", fontSize: 21 * s, lineHeight: 1.35, fontWeight: 500,
        boxShadow: "0 1px 1px rgba(0,0,0,.12)", transform: `scale(${a})`, transformOrigin: out ? "100% 0" : "0 0" }}>
        {text}
        <div style={{ textAlign: "right", fontSize: 13 * s, color: "#667781", marginTop: 4 * s }}>21:04 {out ? <span style={{ color: "#53BDEB" }}>✓✓</span> : null}</div>
      </div>
    );
  };
  const typing = (at: number, until: number) => t >= at && t < until ? (
    <div style={{ alignSelf: "flex-start", marginTop: 12 * s, padding: `${14 * s}px ${18 * s}px`, borderRadius: 16 * s, background: "#fff", display: "flex", gap: 6 * s }}>
      {[0, 1, 2].map((i) => <div key={i} style={{ width: 10 * s, height: 10 * s, borderRadius: "50%", background: "#8696A0",
        transform: `translateY(${-Math.max(0, Math.sin(t * 9 - i * 0.8)) * 6 * s}px)` }} />)}
    </div>
  ) : null;
  const phoneEl = pIn > 0 && fin < 1 ? (
    <>
      {packet > 0 && packet < 1 ? (() => {
        const x0 = fcx + 0.14 * W, y0 = fcy + 0.2 * H, x1 = pcx - pw / 2, y1 = pcy - 0.1 * H;
        const x = x0 + (x1 - x0) * easeIO(packet), y = y0 + (y1 - y0) * easeIO(packet) - Math.sin(packet * Math.PI) * 0.12 * H;
        return <div style={{ position: "absolute", left: x, top: y, width: 22 * s, height: 22 * s, borderRadius: "50%", transform: "translate(-50%,-50%)",
          background: "#fff", boxShadow: `0 0 ${20 * s}px #fff, 0 0 ${50 * s}px ${purple.violet}` }} />;
      })() : null}
      <div style={{ position: "absolute", left: pcx - pw / 2, top: pcy - ph / 2, width: pw, height: ph, borderRadius: 54 * s, background: "#0B0912",
        padding: 12 * s, boxSizing: "border-box", boxShadow: `0 ${40 * s}px ${110 * s}px rgba(0,0,0,.6), 0 0 ${70 * s}px rgba(139,92,246,.35)`,
        transform: `translateX(${(1 - pIn) * 0.35 * W}px) rotate(${(1 - pIn) * 12}deg)`, opacity: Math.min(1, pIn * 2) }}>
        <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 44 * s, overflow: "hidden", background: "#EFE7DE",
          display: "flex", flexDirection: "column", fontFamily: fonts.display }}>
          <div style={{ background: "#075E54", padding: `${44 * s}px ${18 * s}px ${16 * s}px`, display: "flex", alignItems: "center", gap: 12 * s }}>
            <div style={{ width: 48 * s, height: 48 * s, borderRadius: "50%", background: purple.violet, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Img src={staticFile(logo)} style={{ width: 30 * s }} />
            </div>
            <div>
              <div style={{ color: "#fff", fontWeight: 700, fontSize: 22 * s }}>{brand}</div>
              <div style={{ color: "#CFE9E4", fontSize: 16 * s }}>advisor · online</div>
            </div>
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", padding: `${10 * s}px ${14 * s}px` }}>
            {typing(b.chat + 0.6, b.msg1)}
            {bubble(b.msg1, `Salam Yassine! Ana advisor f ${brand}.`)}
            {typing(b.msg1 + 0.4, b.msg2)}
            {bubble(b.msg2, "Ay so2al 3la la formation? Ana hna, n3awnek f kolchi.")}
            {bubble(b.reply, "Bghit nbda lyoum!", true)}
          </div>
        </div>
      </div>
      <div style={{ position: "absolute", left: pcx, top: pcy - ph / 2 - 30 * s, transform: `translate(-50%, -100%) scale(${outBack(seg(t, b.chat + 0.3, b.chat + 0.7))})`,
        padding: `${10 * s}px ${22 * s}px`, borderRadius: 999, background: "#25D366", color: "#fff", fontFamily: fonts.display, fontWeight: 800, fontSize: 28 * s,
        boxShadow: `0 0 ${30 * s}px rgba(37,211,102,.5)` }}>WhatsApp</div>
    </>
  ) : null;

  // ---------- 5. finale ----------
  const flash = t >= b.finale ? Math.max(0, 1 - (t - b.finale) / 0.45) * 0.85 : 0;
  const lg = outBack(seg(t, b.finale + 0.05, b.finale + 0.6));
  const wave = seg(t, b.finale, b.finale + 0.9);
  const letters = brand.split("");
  const urlP = outBack(seg(t, b.finale + 0.75, b.finale + 1.1));
  const ctaP = outBack(seg(t, b.finale + 0.95, b.finale + 1.3));
  const shine = seg(t, b.finale + 1.2, b.finale + 1.9);
  const push = 1 + 0.06 * seg(t, b.finale, D);
  const finale = t >= b.finale - 0.05 ? (
    <AbsoluteFill style={{ transform: `scale(${push})` }}>
      <div style={{ position: "absolute", left: W / 2 - 0.6 * H, top: 0.36 * H - 0.6 * H, width: 1.2 * H, height: 1.2 * H, borderRadius: "50%",
        background: `repeating-conic-gradient(from ${t * 25}deg, rgba(196,181,253,.16) 0deg 8deg, transparent 8deg 22deg)`,
        WebkitMaskImage: "radial-gradient(circle, black 10%, transparent 65%)", maskImage: "radial-gradient(circle, black 10%, transparent 65%)", opacity: lg }} />
      <div style={{ position: "absolute", left: W / 2, top: 0.36 * H, width: 260 * s, height: 260 * s, borderRadius: "50%", transform: `translate(-50%,-50%) scale(${0.3 + wave * 5})`,
        border: `${6 * s}px solid ${purple.lilac}`, opacity: (1 - wave) * 0.8 }} />
      {Array.from({ length: 36 }).map((_, i) => {
        const a = (i / 36) * Math.PI * 2 + rnd(i) * 0.3, d = easeIO(seg(t, b.finale, b.finale + 1.4)) * (0.25 + rnd(i + 11) * 0.3) * W;
        return <div key={i} style={{ position: "absolute", left: W / 2 + Math.cos(a) * d, top: 0.36 * H + Math.sin(a) * d * 0.6, width: 7 * s, height: 7 * s,
          borderRadius: "50%", background: i % 3 ? purple.lilac : "#F0ABFC", opacity: 1 - seg(t, b.finale + 0.6, b.finale + 1.6), boxShadow: `0 0 ${12 * s}px ${purple.violet}` }} />;
      })}
      <Img src={staticFile(logo)} style={{ position: "absolute", left: W / 2, top: 0.36 * H, width: 210 * s, transform: `translate(-50%,-50%) scale(${lg}) rotate(${(1 - lg) * -14}deg)`,
        filter: `drop-shadow(0 0 ${(24 + 14 * Math.sin(t * 3)) * s}px rgba(139,92,246,.95))` }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 0.53 * H, textAlign: "center", fontFamily: fonts.display, fontWeight: 800, fontSize: 104 * s, letterSpacing: -3 * s }}>
        {letters.map((ch, i) => {
          const a = seg(t, b.finale + 0.3 + i * 0.03, b.finale + 0.6 + i * 0.03);
          return <span key={i} style={{ display: "inline-block", whiteSpace: "pre", opacity: a, filter: `blur(${(1 - a) * 10 * s}px)`, transform: `translateY(${(1 - easeIO(a)) * 40 * s}px)`,
            background: `linear-gradient(180deg, #fff, ${purple.lilac})`, WebkitBackgroundClip: "text", backgroundClip: "text", color: "transparent" }}>{ch}</span>;
        })}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 0.72 * H, display: "flex", justifyContent: "center", gap: 26 * s, fontFamily: fonts.display }}>
        <div style={{ position: "relative", overflow: "hidden", padding: `${16 * s}px ${34 * s}px`, borderRadius: 999, border: `${2 * s}px solid rgba(196,181,253,.5)`,
          background: "rgba(29,18,51,.8)", color: purple.white, fontSize: 40 * s, fontWeight: 700, transform: `scale(${urlP})` }}>
          {url}
          <div style={{ position: "absolute", top: 0, bottom: 0, width: "40%", left: `${-40 + shine * 160}%`, background: "linear-gradient(100deg, transparent, rgba(255,255,255,.45), transparent)" }} />
        </div>
        <div style={{ padding: `${16 * s}px ${38 * s}px`, borderRadius: 999, background: `linear-gradient(90deg, ${purple.violet}, #A855F7)`, color: "#fff", fontSize: 40 * s,
          fontWeight: 800, transform: `scale(${ctaP})`, boxShadow: `0 0 0 ${(6 + 6 * Math.sin(t * 4)) * s}px rgba(139,92,246,.25), 0 0 ${50 * s}px rgba(139,92,246,.7)` }}>
          {cta} →
        </div>
      </div>
    </AbsoluteFill>
  ) : null;

  const throughScale = 1 + fin * 0.35;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      {background}
      <AbsoluteFill style={{ transform: `scale(${throughScale})`, opacity: 1 - fin, filter: `blur(${fin * 8 * s}px)` }}>
        {headline1}
        {browser}
        {form}
        {phoneEl}
      </AbsoluteFill>
      {finale}
      {flash > 0 ? <AbsoluteFill style={{ background: "#fff", opacity: flash, mixBlendMode: "screen" }} /> : null}
    </AbsoluteFill>
  );
};
