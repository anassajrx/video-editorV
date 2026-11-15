// Render a list of kept [start, end] segments (seconds) of a clip into one file.
// Used by cut-silences.mjs (rough cut) and for retake/mistake re-cuts.
//
// Usage (CLI): node scripts/render-segments.mjs <input> <segments.json> <output.mp4>
//   segments.json = [[start, end], ...] in seconds of the input.
//
// Low memory: each segment is encoded on its own (frame-accurate seek, 30fps, PCM audio)
// and the parts are joined with the concat demuxer. A single trim+concat filter graph
// buffers decoded frames for every segment and runs out of memory on long 1080p clips.
// Boundaries are snapped to whole frames so audio and video stay in sync after many cuts.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const FPS = 30;

const run = (cmd, args) => {
  const r = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 1 << 28 });
  if (r.status !== 0) throw new Error(`${cmd} failed:\n${r.stderr}`);
  return r;
};

export const snap = (t) => Math.round(t * FPS) / FPS;

/** Returns the snapped segments actually rendered. */
export const renderSegments = (input, segments, output, { crf = 16 } = {}) => {
  const snapped = segments
    .map(([a, b]) => [snap(a), snap(b)])
    .filter(([a, b]) => b - a >= 1 / FPS);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "segs-"));
  const list = [];
  snapped.forEach(([a, b], i) => {
    const part = path.join(tmp, `p${String(i).padStart(4, "0")}.mov`);
    run("ffmpeg", [
      "-hide_banner", "-v", "error", "-y",
      "-ss", a.toFixed(4), "-i", input, "-t", (b - a).toFixed(4),
      "-map", "0:v:0", "-map", "0:a:0",
      "-vf", `fps=${FPS},format=yuv420p`, "-frames:v", String(Math.round((b - a) * FPS)),
      "-c:v", "libx264", "-preset", "veryfast", "-crf", String(crf), "-threads", "4",
      "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2",
      part,
    ]);
    list.push(`file '${part}'`);
  });
  const listFile = path.join(tmp, "list.txt");
  fs.writeFileSync(listFile, list.join("\n"));
  run("ffmpeg", [
    "-hide_banner", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listFile,
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", output,
  ]);
  fs.rmSync(tmp, { recursive: true, force: true });
  return snapped;
};

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [input, segFile, output] = process.argv.slice(2);
  if (!input || !segFile || !output) {
    console.error("Usage: node scripts/render-segments.mjs <input> <segments.json> <output.mp4>");
    process.exit(1);
  }
  const segs = renderSegments(input, JSON.parse(fs.readFileSync(segFile, "utf8")), output);
  const total = segs.reduce((s, [a, b]) => s + b - a, 0);
  console.log(`Rendered ${segs.length} segments (${total.toFixed(2)}s) to ${output}`);
}
