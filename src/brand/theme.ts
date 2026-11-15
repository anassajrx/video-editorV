import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Single source of truth for the brand inside videos.
// Mirrors brand/brand.json — change both together.

export const colors = {
  ink: "#07090F",
  ink2: "#0E1422",
  line: "#22304A",
  text: "#F2F5FA",
  muted: "#8A96AB",
  signal: "#38E1FF",
  signalDeep: "#0A7FA8",
  ember: "#FFB547",
  error: "#FF5C7A",
  success: "#3DF5A6",
} as const;

export type Accent = "signal" | "ember" | "error" | "success";

// Fonts are bundled in public/fonts so renders never depend on Google's CDN.
const FONT_FILES: { family: string; file: string; weight: string; style: string }[] = [
  { family: "Inter Tight", file: "inter-tight-latin-500-normal.woff2", weight: "500", style: "normal" },
  { family: "Inter Tight", file: "inter-tight-latin-700-normal.woff2", weight: "700", style: "normal" },
  { family: "Inter Tight", file: "inter-tight-latin-800-normal.woff2", weight: "800", style: "normal" },
  { family: "Instrument Serif", file: "instrument-serif-latin-400-italic.woff2", weight: "400", style: "italic" },
  { family: "JetBrains Mono", file: "jetbrains-mono-latin-400-normal.woff2", weight: "400", style: "normal" },
  { family: "JetBrains Mono", file: "jetbrains-mono-latin-600-normal.woff2", weight: "600", style: "normal" },
  // Arabic (Darija captions). Arabic subset only: Latin words keep Inter Tight / JetBrains Mono.
  { family: "Cairo", file: "cairo-arabic-500-normal.woff2", weight: "500", style: "normal" },
  { family: "Cairo", file: "cairo-arabic-700-normal.woff2", weight: "700", style: "normal" },
  { family: "Cairo", file: "cairo-arabic-800-normal.woff2", weight: "800", style: "normal" },
  { family: "Cairo", file: "cairo-arabic-900-normal.woff2", weight: "900", style: "normal" },
];
for (const f of FONT_FILES) {
  loadFont({ family: f.family, url: staticFile(`fonts/${f.file}`), weight: f.weight, style: f.style });
}

export const fonts = {
  display: "'Inter Tight', sans-serif",
  serif: "'Instrument Serif', serif",
  mono: "'JetBrains Mono', monospace",
  arabic: "'Cairo', sans-serif",
};

export const glow = (hex: string, strength = 1) =>
  `0 0 ${12 * strength}px ${hex}aa, 0 0 ${36 * strength}px ${hex}55`;

// Canvas presets
export const VERTICAL = { width: 1080, height: 1920 };
export const HORIZONTAL = { width: 1920, height: 1080 };
export const FPS = 30;
