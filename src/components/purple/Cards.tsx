import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, purple } from "../../brand/theme";
import { FrostedCard } from "./FrostedCard";
import { EASE, useProgress } from "./motion";

const ARABIC_RE = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
const isAr = (t: string) => ARABIC_RE.test(t);
const textFont = (t: string): React.CSSProperties =>
  isAr(t) ? { fontFamily: fonts.arabic, fontWeight: 600, direction: "rtl" } : { fontFamily: fonts.display, fontWeight: 500 };

const useS = () => { const { width, height } = useVideoConfig(); return Math.min(width, height) / 1080; };

type Base = { top: number; durationInFrames: number };

/** Avatar dot + comment text + like counter ticking up. */
export const CommentCard: React.FC<Base & { text: string; likes?: number; likesFrom?: number }> = ({
  top,
  durationInFrames,
  text,
  likes = 27,
  likesFrom,
}) => {
  const s = useS();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const from = likesFrom ?? Math.max(0, likes - 8);
  const n = Math.round(
    interpolate(frame, [0.5 * fps, 1.6 * fps], [from, likes], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE }),
  );
  return (
    <FrostedCard top={top} durationInFrames={durationInFrames} width={0.72}>
      <CommentRow text={text} likes={n} s={s} />
    </FrostedCard>
  );
};

const CommentRow: React.FC<{ text: string; likes?: number; s: number }> = ({ text, likes, s }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 20 * s, direction: "ltr" }}>
    <div style={{ width: 34 * s, height: 34 * s, borderRadius: "50%", background: purple.lilac, flexShrink: 0 }} />
    <div style={{ flex: 1, color: purple.white, fontSize: 30 * s, lineHeight: 1.35, ...textFont(text) }}>{text}</div>
    {likes !== undefined ? (
      <div style={{ fontFamily: fonts.mono, fontSize: 26 * s, color: purple.lilac, whiteSpace: "nowrap" }}>♥ {likes}</div>
    ) : null}
  </div>
);

/** Serif chapter number + Arabic label, unfolds left→right. */
export const ChapterChip: React.FC<Base & { number: string; label: string }> = ({ top, durationInFrames, number, label }) => {
  const s = useS();
  const p = useProgress(0, 0.5);
  return (
    <FrostedCard
      top={top}
      durationInFrames={durationInFrames}
      width={0.36}
      style={{ clipPath: `inset(0 ${(1 - p) * 100}% 0 0 round ${20 * s}px)`, padding: `${12 * s}px ${26 * s}px` }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "center", gap: 18 * s, direction: "ltr" }}>
        <span style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 54 * s, color: purple.lilac, lineHeight: 1 }}>
          {number}
        </span>
        <span style={{ fontFamily: fonts.arabic, fontWeight: 600, fontSize: 36 * s, color: purple.white, direction: "rtl" }}>
          {label}
        </span>
      </div>
    </FrostedCard>
  );
};

/** Two labelled bars; the second grows past the first (0.9 s ease-out after 0.5 s). */
export const GapBars: React.FC<
  Base & { a: { label: string; value: number; display?: string }; b: { label: string; value: number; display?: string } }
> = ({ top, durationInFrames, a, b }) => {
  const s = useS();
  const max = Math.max(a.value, b.value);
  const pa = useProgress(0.2, 0.6);
  const pb = useProgress(0.6, 0.9);
  const bar = (label: string, display: string, frac: number, p: number, strong: boolean) => (
    <div style={{ marginBottom: 18 * s }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontFamily: fonts.mono,
          fontSize: 24 * s,
          color: strong ? purple.white : purple.muted,
          marginBottom: 10 * s,
        }}
      >
        <span>{label}</span>
        <span style={{ opacity: p }}>{display}</span>
      </div>
      <div style={{ height: 12 * s, borderRadius: 6 * s, background: "rgba(74,58,107,.45)" }}>
        <div
          style={{
            height: "100%",
            width: `${frac * p * 100}%`,
            borderRadius: 6 * s,
            background: strong ? purple.violet : purple.dim2,
          }}
        />
      </div>
    </div>
  );
  return (
    <FrostedCard top={top} durationInFrames={durationInFrames} width={0.72} style={{ paddingBottom: 6 * s }}>
      <div style={{ direction: "ltr" }}>
        {bar(a.label, a.display ?? String(a.value), a.value / max, pa, false)}
        {bar(b.label, b.display ?? String(b.value), b.value / max, pb, true)}
      </div>
    </FrostedCard>
  );
};

/** The opening comment with a "PINNED" reply sliding in under it (closes the loop). */
export const PinnedReply: React.FC<Base & { comment: string; reply: string }> = ({ top, durationInFrames, comment, reply }) => {
  const s = useS();
  const p = useProgress(0.5, 0.5);
  return (
    <FrostedCard top={top} durationInFrames={durationInFrames} width={0.72}>
      <CommentRow text={comment} s={s} />
      <div
        style={{
          marginTop: 16 * s,
          border: `${Math.max(1, s)}px solid ${purple.violet}`,
          borderRadius: purple.cardRadius * s * 1.6,
          padding: `${12 * s}px ${22 * s}px`,
          display: "flex",
          alignItems: "center",
          gap: 18 * s,
          direction: "ltr",
          opacity: p,
          transform: `translateY(${(1 - p) * -14 * s}px)`,
        }}
      >
        <span style={{ fontFamily: fonts.mono, fontSize: 20 * s, color: purple.lilac, letterSpacing: 2 * s }}>PINNED</span>
        <span style={{ color: purple.white, fontSize: 30 * s, ...textFont(reply) }}>{reply} ✓</span>
      </div>
    </FrostedCard>
  );
};
