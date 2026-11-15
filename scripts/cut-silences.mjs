// Rough cut: removes silences/pauses from a raw talking-head clip.
// Usage: npm run cut -- <input.mp4> <output.mp4> [--noise=-35dB] [--min=0.35] [--pad=0.08]
// Output: tight jump-cut clip + <output>.cuts.json (kept segments, used to place punch-ins).
import { spawnSync } from "node:child_process";
import fs from "node:fs";

const [input, output, ...flags] = process.argv.slice(2);
if (!input || !output) {
  console.error("Usage: npm run cut -- <input> <output> [--noise=-35dB] [--min=0.35] [--pad=0.08]");
  process.exit(1);
}
const opt = Object.fromEntries(flags.map((f) => f.replace(/^--/, "").split("=")));
const noise = opt.noise ?? "-35dB";
const minSilence = Number(opt.min ?? 0.35);
const pad = Number(opt.pad ?? 0.08);

const run = (cmd, args) => {
  const r = spawnSync(cmd, args, { encoding: "utf8", maxBuffer: 1 << 28 });
  if (r.status !== 0) throw new Error(`${cmd} failed:\n${r.stderr}`);
  return r;
};

const duration = Number(
  run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", input]).stdout.trim(),
);
const log = run("ffmpeg", ["-hide_banner", "-i", input, "-af", `silencedetect=n=${noise}:d=${minSilence}`, "-f", "null", "-"]).stderr;

const starts = [...log.matchAll(/silence_start: ([\d.]+)/g)].map((m) => Number(m[1]));
const ends = [...log.matchAll(/silence_end: ([\d.]+)/g)].map((m) => Number(m[1]));

// Build "keep" segments between silences, padded so words aren't clipped.
const keep = [];
let cursor = 0;
starts.forEach((s, i) => {
  const segEnd = Math.min(duration, s + pad);
  if (segEnd - cursor > 0.15) keep.push([Math.max(0, cursor), segEnd]);
  cursor = Math.max(0, (ends[i] ?? duration) - pad);
});
if (duration - cursor > 0.15) keep.push([cursor, duration]);

if (keep.length === 0) {
  console.error("Nothing left after cutting. Try --noise=-45dB or a bigger --min.");
  process.exit(1);
}

const parts = keep
  .map(([a, b], i) => `[0:v]trim=${a}:${b},setpts=PTS-STARTPTS[v${i}];[0:a]atrim=${a}:${b},asetpts=PTS-STARTPTS[a${i}];`)
  .join("");
const concat = keep.map((_, i) => `[v${i}][a${i}]`).join("") + `concat=n=${keep.length}:v=1:a=1[v][a]`;

run("ffmpeg", [
  "-hide_banner", "-y", "-i", input,
  "-filter_complex", parts + concat,
  "-map", "[v]", "-map", "[a]",
  "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
  "-c:a", "aac", "-b:a", "192k",
  output,
]);

// Output timeline positions of every jump cut (useful for punch-ins).
let t = 0;
const cuts = keep.map(([a, b]) => {
  const seg = { sourceStart: a, sourceEnd: b, outStartMs: Math.round(t * 1000) };
  t += b - a;
  return seg;
});
fs.writeFileSync(`${output}.cuts.json`, JSON.stringify({ input, removedSeconds: +(duration - t).toFixed(2), cuts }, null, 2));
console.log(`Kept ${keep.length} segments. ${duration.toFixed(1)}s -> ${t.toFixed(1)}s. Cuts written to ${output}.cuts.json`);
