import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, purple } from "../../brand/theme";
import { LineIcon, type IconName } from "../Icons";
import { outBack } from "./Moments";

const cl = (x: number) => Math.max(0, Math.min(1, x));

/**
 * Horizontal (16:9) talking parts: a frosted card that springs in from the LEFT or RIGHT edge, beside the face,
 * never over or above it (check_face.py checks the faceZone left..right columns). Icon tile with glow, a bold
 * word, an optional small line, an accent bar that draws itself, a slow float, and a slide back out.
 * `y` = vertical centre (0..1 of the frame height).
 */
export const SideChip: React.FC<{ durationInFrames: number; text: string; sub?: string; icon?: IconName; side?: "left" | "right"; y?: number }> = ({
  durationInFrames, text, sub, icon = "sparkles", side = "left", y = 0.42,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const s = Math.min(W, H) / 1080;
  const t = frame / fps;
  const D = durationInFrames / fps;
  const inP = outBack(cl(t / 0.5));
  const out = cl((t - (D - 0.35)) / 0.35);
  const dir = side === "left" ? -1 : 1;
  const bar = interpolate(t, [0.35, 0.9], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const icP = outBack(cl((t - 0.15) / 0.45));
  const subP = cl((t - 0.4) / 0.35);
  const float = Math.sin(t * 2.2) * 6 * s;
  const glow = 0.5 + 0.5 * Math.sin(t * 3);
  const edge = 0.035 * W;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{
        position: "absolute", top: y * H, [side]: edge, maxWidth: 0.24 * W,
        transform: `translate(${dir * ((1 - inP) * 0.3 * W + out * 0.3 * W)}px, calc(-50% + ${float}px)) rotate(${dir * (1 - inP) * 6}deg)`,
        opacity: cl(inP * 2) * (1 - out),
        display: "flex", alignItems: "center", gap: 16 * s, padding: `${16 * s}px ${24 * s}px ${16 * s}px ${16 * s}px`,
        borderRadius: 22 * s, background: purple.card, border: `${1.5 * s}px solid ${purple.cardBorder}`, backdropFilter: `blur(${14 * s}px)`,
        boxShadow: `0 ${24 * s}px ${60 * s}px rgba(0,0,0,.45), 0 0 ${40 * s}px rgba(139,92,246,${0.2 + 0.15 * glow})`,
      }}>
        <div style={{ flex: "none", width: 64 * s, height: 64 * s, borderRadius: 16 * s, background: `linear-gradient(135deg, ${purple.violet}, #6D28D9)`,
          display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${icP}) rotate(${(1 - icP) * -20}deg)`,
          boxShadow: `0 0 ${(18 + 16 * glow) * s}px rgba(139,92,246,.8)` }}>
          <LineIcon name={icon} size={36 * s} color="#fff" />
        </div>
        <div style={{ fontFamily: fonts.display, minWidth: 0 }}>
          <div style={{ fontSize: 34 * s, fontWeight: 800, color: purple.white, letterSpacing: -0.8 * s, lineHeight: 1.1, whiteSpace: "nowrap" }}>{text}</div>
          {sub ? <div style={{ marginTop: 6 * s, fontSize: 21 * s, color: purple.lilac, opacity: subP, transform: `translateY(${(1 - subP) * 8 * s}px)`, whiteSpace: "nowrap" }}>{sub}</div> : null}
          <div style={{ marginTop: 10 * s, height: 4 * s, width: `${bar * 100}%`, borderRadius: 4 * s, background: `linear-gradient(90deg, ${purple.violet}, #F0ABFC)` }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
