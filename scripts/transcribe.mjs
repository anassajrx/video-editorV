// Word-level transcription with Whisper (runs in the cloud session, no API key).
// Usage: npm run transcribe -- <input.mp4> <output.json> [--model=base.en]
// Output: Caption[] JSON (text, startMs, endMs) — Claude then adds a `role` to each word.
import path from "node:path";
import fs from "node:fs";
import { spawnSync } from "node:child_process";
import {
  downloadWhisperModel,
  installWhisperCpp,
  transcribe,
  toCaptions,
} from "@remotion/install-whisper-cpp";

const [input, output, ...flags] = process.argv.slice(2);
if (!input || !output) {
  console.error("Usage: npm run transcribe -- <input> <output.json> [--model=base.en]");
  process.exit(1);
}
const opt = Object.fromEntries(flags.map((f) => f.replace(/^--/, "").split("=")));
// Use "medium" (not .en) if you speak Arabic/French/Darija in the video.
const model = opt.model ?? "base.en";

const whisperDir = path.join(process.cwd(), ".whisper");
await installWhisperCpp({ to: whisperDir, version: "1.5.5" });
await downloadWhisperModel({ model, folder: whisperDir });

const wav = path.join(whisperDir, "tmp-16k.wav");
const r = spawnSync("ffmpeg", ["-hide_banner", "-y", "-i", input, "-ar", "16000", "-ac", "1", wav], { encoding: "utf8" });
if (r.status !== 0) throw new Error(r.stderr);

const whisperCppOutput = await transcribe({
  model,
  whisperPath: whisperDir,
  whisperCppVersion: "1.5.5",
  inputPath: wav,
  tokenLevelTimestamps: true,
});
const { captions } = toCaptions({ whisperCppOutput });
// Merge sub-word tokens and punctuation (no leading space) into the previous word.
const words = [];
for (const c of captions) {
  const prev = words[words.length - 1];
  if (prev && (!c.text.startsWith(" ") || /^\s*[.,!?;:'"…-]+\s*$/.test(c.text))) {
    prev.text += c.text.trim();
    prev.endMs = Math.max(prev.endMs, c.endMs);
  } else if (c.text.trim()) {
    words.push({ text: c.text.trim(), startMs: c.startMs, endMs: c.endMs });
  }
}
fs.writeFileSync(output, JSON.stringify(words, null, 2));
console.log(`Wrote ${words.length} words to ${output}`);
