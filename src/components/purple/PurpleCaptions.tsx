import React, { useMemo } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, purple } from "../../brand/theme";
import type { StyledWord } from "../../brand/types";
import { EASE } from "./motion";

const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const isAr = (t: string) => ARABIC_RE.test(t);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const MAX_PER_LINE = 4;
/** Top of the caption block during full-screen moments (no face on screen). */
export const MOMENT_CAPTION_TOP = 0.14;

const toPages = (words: StyledWord[]) => {
  const pages: StyledWord[][] = [];
  let cur: StyledWord[] = [];
  for (const w of words) {
    cur.push(w);
    if (w.pageBreakAfter || cur.length >= MAX_PER_LINE * 2) {
      pages.push(cur);
      cur = [];
    }
  }
  if (cur.length) pages.push(cur);
  return pages;
};

const toLines = (page: StyledWord[]) => {
  if (page.length <= 2) return [page];
  const first = Math.min(MAX_PER_LINE, Math.ceil(page.length / 2));
  return [page.slice(0, first), page.slice(first)];
};

const Word: React.FC<{ w: StyledWord; s: number; nowMs: number; dim: boolean }> = ({ w, s, nowMs, dim }) => {
  const ar = isAr(w.text);
  const pill = w.role === "pill" || w.role === "hero";
  const base: React.CSSProperties = ar
    ? { fontFamily: fonts.arabic, fontWeight: pill ? 800 : 600, fontSize: 62 * s, letterSpacing: 0 }
    : { fontFamily: fonts.display, fontWeight: pill ? 800 : 500, fontSize: 56 * s, letterSpacing: -1 * s };
  if (!pill) {
    return (
      <span dir={ar ? "rtl" : "ltr"} style={{ ...base, color: purple.white, margin: `0 ${9 * s}px`, display: "inline-block", opacity: dim ? 0.6 : 1 }}>
        {w.text}
      </span>
    );
  }
  // ONE key word per page: white text on a violet pill that wipes in right-to-left (0.3 s) when the word is said.
  const p = interpolate(nowMs, [w.startMs, w.startMs + 300], [0, 1], { ...clamp, easing: EASE });
  return (
    <span style={{ position: "relative", display: "inline-block", margin: `0 ${9 * s}px`, padding: `0 ${16 * s}px` }}>
      <span
        style={{
          position: "absolute",
          inset: `${(ar ? 10 : 4) * s}px 0 ${(ar ? 6 : 2) * s}px 0`,
          background: purple.violet,
          borderRadius: purple.pillRadius * s * 1.4,
          clipPath: `inset(0 0 0 ${(1 - p) * 100}%)`,
        }}
      />
      <span dir={ar ? "rtl" : "ltr"} style={{ ...base, position: "relative", color: purple.white, textShadow: "none" }}>
        {w.text}
      </span>
    </span>
  );
};

/**
 * Purple Room captions: two calm lines (max 4 words each) under the chin, Alexandria 600 white with a soft shadow,
 * second line at 60 % (the pill word always stays at 100 %), one pill word per page. During full-screen moments they move to the top.
 */
export const PurpleCaptions: React.FC<{
  words: StyledWord[];
  top: number;
  momentRanges?: { startMs: number; endMs: number }[];
}> = ({ words, top, momentRanges = [] }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const s = width / 1080;
  const pages = useMemo(() => toPages(words), [words]);
  const nowMs = (frame / fps) * 1000;

  const idx = pages.findIndex((pg, i) => {
    const next = pages[i + 1];
    const end = Math.min(pg[pg.length - 1].endMs + 300, next ? next[0].startMs : Infinity);
    return nowMs >= pg[0].startMs - 150 && nowMs < end;
  });
  if (idx === -1) return null;
  const page = pages[idx];
  const next = pages[idx + 1];
  const startMs = page[0].startMs - 150;
  const endMs = Math.min(page[page.length - 1].endMs + 300, next ? next[0].startMs : Infinity);
  const enter = interpolate(nowMs, [startMs, startMs + 250], [0, 1], { ...clamp, easing: EASE });
  const exit = interpolate(nowMs, [endMs - 150, endMs], [1, 0], { ...clamp, easing: EASE });
  // Top position ONLY while a full-screen moment is actually on screen (the face is hidden then).
  // A page that straddles a moment edge stays under the chin outside the moment, and is hidden while it switches.
  const inMoment = momentRanges.some((r) => nowMs >= r.startMs && nowMs < r.endMs);
  const rtl = page.some((w) => isAr(w.text));

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: "6%",
          right: "6%",
          top: `${(inMoment ? MOMENT_CAPTION_TOP : top) * 100}%`,
          direction: rtl ? "rtl" : "ltr",
          textAlign: "center",
          opacity: enter * exit,
          transform: `translateY(${(1 - enter) * 10 * s}px)`,
          textShadow: purple.captionShadow,
        }}
      >
        {toLines(page).map((line, li) => (
          <div key={li} style={{ lineHeight: 1.45, whiteSpace: "nowrap" }}>
            {line.map((w, i) => (
              <Word key={i} w={w} s={s} nowMs={nowMs} dim={li > 0} />
            ))}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
