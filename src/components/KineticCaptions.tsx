import React, { useMemo } from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { colors, fonts, glow } from "../brand/theme";
import type { StyledWord, WordRole } from "../brand/types";

const MAX_WORDS_PER_PAGE = 5;

const roleStyle = (role: WordRole, scale: number): React.CSSProperties => {
  const s = (px: number) => px * scale;
  switch (role) {
    case "soft":
      return { fontFamily: fonts.display, fontWeight: 500, fontSize: s(44), color: colors.muted, letterSpacing: -0.5 };
    case "hero":
      return { fontFamily: fonts.display, fontWeight: 800, fontSize: s(124), color: colors.text, letterSpacing: -4 };
    case "serif":
      return { fontFamily: fonts.serif, fontStyle: "italic", fontWeight: 400, fontSize: s(104), color: colors.text, letterSpacing: -1 };
    case "signal":
      return { fontFamily: fonts.display, fontWeight: 800, fontSize: s(100), color: colors.signal, textShadow: glow(colors.signal), letterSpacing: -3 };
    case "ember":
      return { fontFamily: fonts.display, fontWeight: 800, fontSize: s(112), color: colors.ember, textShadow: glow(colors.ember, 0.8), letterSpacing: -3 };
    case "mono":
      return { fontFamily: fonts.mono, fontWeight: 600, fontSize: s(56), color: colors.signal, textShadow: glow(colors.signal, 0.6) };
    case "error":
      return { fontFamily: fonts.display, fontWeight: 800, fontSize: s(100), color: colors.error, textShadow: glow(colors.error, 0.8), letterSpacing: -3 };
    default:
      return { fontFamily: fonts.display, fontWeight: 700, fontSize: s(76), color: colors.text, letterSpacing: -2 };
  }
};

const toPages = (words: StyledWord[]) => {
  const pages: StyledWord[][] = [];
  let cur: StyledWord[] = [];
  for (const w of words) {
    cur.push(w);
    if (w.pageBreakAfter || cur.length >= MAX_WORDS_PER_PAGE) {
      pages.push(cur);
      cur = [];
    }
  }
  if (cur.length) pages.push(cur);
  return pages;
};

const Word: React.FC<{ w: StyledWord; scale: number; pageStartMs: number }> = ({ w, scale }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startFrame = (w.startMs / 1000) * fps;
  const p = spring({ frame: frame - startFrame, fps, config: { damping: 18, stiffness: 220, mass: 0.6 } });
  const visible = frame >= startFrame - 1;
  return (
    <span
      style={{
        ...roleStyle(w.role ?? "default", scale),
        display: "inline-block",
        lineHeight: 0.95,
        margin: `0 ${10 * scale}px`,
        opacity: visible ? interpolate(p, [0, 1], [0, 1]) : 0,
        scale: String(interpolate(p, [0, 1], [0.7, 1])),
        translate: `0px ${interpolate(p, [0, 1], [24, 0])}px`,
        filter: `blur(${interpolate(p, [0, 1], [10, 0])}px)`,
      }}
    >
      {w.text}
    </span>
  );
};

export const KineticCaptions: React.FC<{ words: StyledWord[]; top: number }> = ({ words, top }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const scale = width / 1080;
  const pages = useMemo(() => toPages(words), [words]);
  const nowMs = (frame / fps) * 1000;

  const pageIndex = pages.findIndex((pg, i) => {
    const start = pg[0].startMs;
    const next = pages[i + 1];
    const end = Math.min(pg[pg.length - 1].endMs + 250, next ? next[0].startMs : Infinity);
    return nowMs >= start && nowMs < end;
  });
  if (pageIndex === -1) return null;
  const page = pages[pageIndex];
  const pageEnd = page[page.length - 1].endMs + 250;
  const exit = interpolate(nowMs, [pageEnd - 120, pageEnd], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: "7%",
          right: "7%",
          top: `${top * 100}%`,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "baseline",
          alignContent: "flex-start",
          rowGap: 4 * scale,
          textAlign: "center",
          opacity: exit,
          textShadow: "0 6px 30px rgba(0,0,0,0.55)",
        }}
      >
        {page.map((w, i) => (
          <Word key={i} w={w} scale={scale} pageStartMs={page[0].startMs} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
