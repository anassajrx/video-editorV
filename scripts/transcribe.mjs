// Word-level transcription with Whisper (runs in the cloud session, no API key).
// Usage: npm run transcribe -- <input.mp4> <output.json> [--lang=ar] [--model=large-v3]
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
  console.error("Usage: npm run transcribe -- <input> <output.json> [--lang=ar] [--model=large-v3]");
  process.exit(1);
}
const opt = Object.fromEntries(flags.map((f) => f.replace(/^--/, "").split("=")));
// --lang: spoken language passed to Whisper ("en", "ar", "fr"...). Darija videos use --lang=ar.
const lang = opt.lang ?? "en";
// Non-English needs a multilingual model: large-v3 by default (use --model=medium if it is too slow/big).
const model = opt.model ?? (lang === "en" ? "base.en" : "large-v3");
console.log(`Transcribing with model=${model} language=${lang}`);

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
  language: lang,
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
