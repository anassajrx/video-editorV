import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Single source of truth for the brand inside videos.
// Brand tokens. The Purple Room style tokens live in the darija-video-edit-local skill (section 6.1).

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
  // Arabic (Darija captions): Alexandria (Purple Room), arabic subset only. Latin words keep Inter Tight / JetBrains Mono.
  // Cairo files stay in public/fonts for old edits but are no longer used.
  { family: "Alexandria", file: "alexandria-arabic-600-normal.woff2", weight: "600", style: "normal" },
  { family: "Alexandria", file: "alexandria-arabic-800-normal.woff2", weight: "800", style: "normal" },
];
for (const f of FONT_FILES) {
  loadFont({ family: f.family, url: staticFile(`fonts/${f.file}`), weight: f.weight, style: f.style });
}

export const fonts = {
  display: "'Inter Tight', sans-serif",
  serif: "'Instrument Serif', serif",
  mono: "'JetBrains Mono', monospace",
  arabic: "'Alexandria', sans-serif",
};

// "Purple Room" style tokens (darija-video-edit-local skill, section 6.1). No orange, no blue, no glow.
export const purple = {
  plum: "#120A1F",
  plumCentre: "#2A1A4A",
  violet: "#8B5CF6",
  lilac: "#C4B5FD",
  white: "#F5F3FF",
  muted: "#9A8FB5",
  dim: "#3B2A63",
  dim2: "#4A3A6B",
  card: "rgba(29,18,51,.82)",
  cardBorder: "rgba(196,181,253,.25)",
  cardRadius: 12,
  pillRadius: 7,
  captionShadow: "0 2px 18px rgba(10,5,20,.55), 0 1px 3px rgba(10,5,20,.6)",
} as const;

/** Full-screen plum background (radial to plumCentre in the middle). */
export const plumBackground = `radial-gradient(ellipse 75% 60% at 50% 50%, ${purple.plumCentre} 0%, ${purple.plum} 100%)`;

export const glow = (hex: string, strength = 1) =>
  `0 0 ${12 * strength}px ${hex}aa, 0 0 ${36 * strength}px ${hex}55`;

// Canvas presets
export const VERTICAL = { width: 1080, height: 1920 };
export const HORIZONTAL = { width: 1920, height: 1080 };
export const FPS = 30;
