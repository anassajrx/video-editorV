import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, purple } from "../../brand/theme";
import { FrostedCard } from "./FrostedCard";
import { EASE, useProgress } from "./motion";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const useS = () => { const { width, height } = useVideoConfig(); return Math.min(width, height) / 1080; };
type Base = { top: number; durationInFrames: number };

/** Mono lines stacking one by one (e.g. video_final_v9_final_wallah_final.mp4); older lines fade up. */
export const FileStack: React.FC<Base & { lines: string[]; every?: number }> = ({ top, durationInFrames, lines, every = 0.5 }) => {
  const s = useS();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const shown = lines.map((_, i) =>
    interpolate(frame, [(0.3 + i * every) * fps, (0.3 + i * every + 0.4) * fps], [0, 1], { ...clamp, easing: EASE }),
  );
  const visible = shown.filter((p) => p > 0).length;
  return (
    <FrostedCard top={top} durationInFrames={durationInFrames} width={0.8}>
      <div style={{ fontFamily: fonts.mono, fontSize: 25 * s, lineHeight: 1.75, direction: "ltr" }}>
        {lines.map((l, i) => {
          const age = Math.max(0, visible - 1 - i);
          return (
            <div
              key={i}
              style={{
                opacity: shown[i] * (age === 0 ? 1 : age === 1 ? 0.55 : 0.3),
                color: age === 0 ? purple.white : purple.muted,
                transform: `translateY(${(1 - shown[i]) * 12 * s}px)`,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                height: shown[i] > 0 ? undefined : 0,
              }}
            >
              {l}
            </div>
          );
        })}
      </div>
    </FrostedCard>
  );
};

/** A progress bar that crawls and gets stuck (e.g. "03:00 AM · timeline" 21→23 %). */
export const ProgressCard: React.FC<Base & { label: string; from: number; to: number }> = ({ top, durationInFrames, label, from, to }) => {
  const s = useS();
  const p = useProgress(0.4, 1.6);
  const v = from + (to - from) * p;
  return (
    <FrostedCard top={top} durationInFrames={durationInFrames} width={0.72}>
      <div style={{ display: "flex", justifyContent: "space-between", fontFamily: fonts.mono, fontSize: 25 * s, color: purple.muted, direction: "ltr" }}>
        <span>{label}</span>
        <span style={{ color: purple.white }}>{Math.round(v)}%</span>
      </div>
      <div style={{ height: 12 * s, borderRadius: 6 * s, background: "rgba(74,58,107,.45)", marginTop: 14 * s, marginBottom: 6 * s }}>
        <div style={{ height: "100%", width: `${v}%`, borderRadius: 6 * s, background: purple.dim2 }} />
      </div>
    </FrostedCard>
  );
};

/** Rows "cut ······ Claude" ticking in one by one (the twist recap). */
export const CreditRows: React.FC<Base & { rows: string[]; who: string; every?: number }> = ({ top, durationInFrames, rows, who, every = 0.4 }) => {
  const s = useS();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <FrostedCard top={top} durationInFrames={durationInFrames} width={0.7}>
      <div style={{ fontFamily: fonts.mono, fontSize: 26 * s, lineHeight: 1.6, direction: "ltr" }}>
        {rows.map((r, i) => {
          const p = interpolate(frame, [(0.3 + i * every) * fps, (0.3 + i * every + 0.35) * fps], [0, 1], { ...clamp, easing: EASE });
          return (
            <div key={i} style={{ display: "flex", gap: 14 * s, opacity: p, transform: `translateX(${(1 - p) * -14 * s}px)` }}>
              <span style={{ color: purple.white }}>{r}</span>
              <span style={{ flex: 1, borderBottom: `${2 * s}px dotted ${purple.dim2}`, transform: `translateY(${-10 * s}px)` }} />
              <span style={{ color: purple.lilac }}>{who}</span>
            </div>
          );
        })}
      </div>
    </FrostedCard>
  );
};
