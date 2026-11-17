import type { Accent } from "./theme";
import type { IconName } from "../components/Icons";

/**
 * Caption word roles — this is what gives the "mixed typography" look.
 * default : bold white sans (most words)
 * soft    : small, light, grey filler words (a, the, was, in, to...)
 * hero    : huge bold word — 1 per page max
 * serif   : italic serif — emotional / human words
 * signal  : cyan glowing — tech / key concept words
 * ember   : amber — money, numbers, results
 * mono    : monospace cyan — code, tools, commands
 * error   : red — doubt, failure, bugs
 * pill    : Purple Room — the ONE key word per page, white on a violet pill (PurpleCaptions)
 */
export type WordRole =
  | "default"
  | "soft"
  | "hero"
  | "serif"
  | "signal"
  | "ember"
  | "mono"
  | "error"
  | "pill";

export type StyledWord = {
  text: string;
  startMs: number;
  endMs: number;
  role?: WordRole;
  pageBreakAfter?: boolean;
};

type Timed = { startMs: number; endMs: number };

export type Overlay =
  | (Timed & {
      type: "card";
      title: string;
      subtitle?: string;
      tag?: string;
      accent?: Accent;
      x?: number; // 0..1 centre
      y?: number; // 0..1 top edge (clamped below the face)
    })
  | (Timed & {
      type: "profile";
      name: string;
      avatar: string; // path inside public/
      lines: string[];
      y?: number;
    })
  | (Timed & {
      type: "timeline";
      steps: string[];
      fromIndex: number;
      toIndex: number;
      moveAtMs?: number;
      avatar?: string;
      y?: number;
    })
  | (Timed & {
      type: "terminal";
      title?: string;
      lines: string[];
      y?: number;
    })
  | (Timed & {
      type: "stat";
      value: string;
      label: string;
      accent?: Accent;
      y?: number;
    })
  | (Timed & {
      type: "icon";
      icon: IconName; // see src/components/Icons.tsx
      label?: string; // short mono label under the icon (Latin)
      accent?: Accent;
      x?: number; // 0..1 centre
      y?: number;
    })
  | (Timed & {
      type: "image";
      src: string; // screenshot / tweet / b-roll still in public/
      y?: number;
      width?: number; // 0..1 of frame width
    });

/** Purple Room overlays (src/components/purple). Under-chin ones are clamped below the caption band;
 *  "moment*" and "endCard" are full-screen (no face on screen) and move the captions to the top. */
export type PurpleOverlay =
  | (Timed & { type: "comment"; text: string; likes?: number; likesFrom?: number; y?: number })
  | (Timed & { type: "chapterChip"; number: string; label: string; y?: number })
  | (Timed & {
      type: "gapBars";
      a: { label: string; value: number; display?: string };
      b: { label: string; value: number; display?: string };
      y?: number;
    })
  | (Timed & { type: "pinnedReply"; comment: string; reply: string; y?: number })
  | (Timed & { type: "chapterBlur"; number: string; label?: string })
  | (Timed & { type: "bwStrike"; word: string; strikeAtMs?: number })
  | (Timed & { type: "momentBlocks"; label?: string })
  | (Timed & { type: "momentCounter"; steps: number[]; value: string; unit: string; kicker?: string })
  | (Timed & { type: "momentSlider"; label: string; kicker?: string; percent?: number })
  | (Timed & { type: "momentCode"; code: string; sub?: string; file?: string })
  | (Timed & { type: "endCard"; line: string; handle: string })
  | (Timed & { type: "fileStack"; lines: string[]; every?: number; y?: number })
  | (Timed & { type: "progressCard"; label: string; from: number; to: number; y?: number })
  | (Timed & { type: "creditRows"; rows: string[]; who: string; every?: number; y?: number })
  | (Timed & { type: "momentFlow"; words: string[] })
  | (Timed & { type: "ctaEndCard"; kicker: string; word: string; sub?: string })
  /** Full-frame muted footage clip (e.g. a pre-reversed "rewind" piece of the edit). Hidden in QA renders. */
  | (Timed & { type: "clip"; src: string });

export const FULL_SCREEN_TYPES = [
  "momentBlocks",
  "momentCounter",
  "momentSlider",
  "momentCode",
  "momentFlow",
  "endCard",
  "ctaEndCard",
] as const;

export type EditSpec = {
  /** "purple" = Purple Room style (Alexandria captions + violet pill, soft push-ins, no cyan grade). */
  style?: "classic" | "purple";
  orientation: "vertical" | "horizontal";
  durationMs: number;
  footage: {
    src: string; // path inside public/
    kind: "video" | "image";
    trimBeforeMs?: number;
  };
  punchIns?: { atMs: number; scale: number }[];
  monoRanges?: { startMs: number; endMs: number }[]; // black & white "doubt" moments
  captions: StyledWord[];
  captionY?: number; // 0..1 TOP of the caption block; clamped below faceZone.bottom
  /** Protected face area (0..1 of frame height). Written by scripts/face_zone.py. NOTHING may be drawn inside or above it. */
  faceZone?: { top: number; bottom: number };
  overlays: (Overlay | PurpleOverlay)[];
  music?: { src: string; volume: number; fadeInMs?: number; fadeOutMs?: number };
  sfx?: { src: string; atMs: number; volume?: number }[];
};
