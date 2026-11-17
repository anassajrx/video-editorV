import React from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { purple } from "../../brand/theme";
import { useEnterExit } from "./motion";

/** The frosted plum under-chin card shell. `top` is 0..1 of frame height (already clamped below the face). */
export const FrostedCard: React.FC<{
  top: number;
  durationInFrames: number;
  width?: number; // 0..1 of the SHORT side (= frame width in vertical)
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ top, durationInFrames, width = 0.74, children, style }) => {
  const { width: W, height: H } = useVideoConfig();
  const s = Math.min(W, H) / 1080;
  const { opacity, translateY } = useEnterExit(durationInFrames);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: `${top * 100}%`,
          left: (W - width * Math.min(W, H)) / 2,
          width: width * Math.min(W, H),
          boxSizing: "border-box",
          background: purple.card,
          border: `${Math.max(1, s)}px solid ${purple.cardBorder}`,
          borderRadius: purple.cardRadius * s * 1.6,
          backdropFilter: `blur(${14 * s}px)`,
          padding: `${22 * s}px ${30 * s}px`,
          opacity,
          transform: `translateY(${translateY * s}px)`,
          ...style,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};
