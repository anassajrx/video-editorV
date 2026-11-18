// Resumable render: renders a composition in chunks of N frames (video only), skips chunks already on disk,
// renders the audio once, then joins everything. Survives container restarts: just run it again.
// Usage: node scripts/render-chunks.mjs <compositionId> <out.mp4> [chunkFrames=300] [crf=18]
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [, , id, out, chunkArg = "300", crfArg = "18"] = process.argv;
const N = parseInt(chunkArg, 10);
const dir = path.join(path.dirname(out), `${id}-chunks`);
fs.mkdirSync(dir, { recursive: true });
const serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts") });
const composition = await selectComposition({ serveUrl, id });
const total = composition.durationInFrames;
const chunks = [];
for (let a = 0; a < total; a += N) chunks.push([a, Math.min(total, a + N) - 1]);
const t0 = Date.now();
let doneFrames = chunks.filter((_, i) => fs.existsSync(path.join(dir, `c${String(i).padStart(3, "0")}.mp4`)))
  .reduce((s, [a, b]) => s + b - a + 1, 0);
const startDone = doneFrames;
for (const [i, [a, b]] of chunks.entries()) {
  const f = path.join(dir, `c${String(i).padStart(3, "0")}.mp4`);
  if (fs.existsSync(f)) continue;
  await renderMedia({ composition, serveUrl, codec: "h264", crf: parseInt(crfArg, 10), muted: true, frameRange: [a, b],
    outputLocation: f.replace(/\.mp4$/, ".part.mp4"), concurrency: "100%" });
  fs.renameSync(f.replace(/\.mp4$/, ".part.mp4"), f);
  doneFrames += b - a + 1;
  const rate = (doneFrames - startDone) / ((Date.now() - t0) / 1000);
  console.log(`PROGRESS ${doneFrames}/${total} frames (${Math.round((100 * doneFrames) / total)}%), ~${((total - doneFrames) / rate / 60).toFixed(1)} min left`);
}
const wav = path.join(dir, "audio.wav");
if (!fs.existsSync(wav)) {
  await renderMedia({ composition, serveUrl, codec: "wav", outputLocation: wav + ".part.wav" });
  fs.renameSync(wav + ".part.wav", wav);
  console.log("PROGRESS audio done");
}
const list = path.join(dir, "list.txt");
fs.writeFileSync(list, chunks.map((_, i) => `file 'c${String(i).padStart(3, "0")}.mp4'`).join("\n"));
const r = spawnSync("ffmpeg", ["-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", list, "-i", wav, "-map", "0:v", "-map", "1:a",
  "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out], { encoding: "utf8" });
if (r.status !== 0) throw new Error(r.stderr);
console.log("DONE", out);
