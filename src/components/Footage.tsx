import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { colors } from "../brand/theme";
import type { EditSpec } from "../brand/types";

export const Footage: React.FC<{ spec: EditSpec }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const nowMs = (frame / fps) * 1000;

  // Slow constant push-in (1.00 -> 1.05) + instant punch-ins on jump cuts.
  const push = interpolate(frame, [0, durationInFrames], [1, 1.05]);
  const punch = [...(spec.punchIns ?? [])].filter((p) => p.atMs <= nowMs).sort((a, b) => b.atMs - a.atMs)[0];
  const purple = spec.style === "purple";
  // Purple Room: no jumpy punch-ins. Each punchIn eases from the previous scale to its own over ~3 s (1.00 -> 1.08).
  const pushIns = [...(spec.punchIns ?? [])].sort((a, b) => a.atMs - b.atMs);
  let eased = 1;
  for (const p of pushIns) {
    if (p.atMs > nowMs) break;
    if (p.atMs === 0) {
      eased = p.scale; // the opening scale applies from frame 0
      continue;
    }
    eased = interpolate(nowMs, [p.atMs, p.atMs + 3000], [eased, p.scale], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });
  }
  const scale = purple ? eased : push * (punch?.scale ?? 1);

  // Black & white "doubt" moments with a quick 4-frame fade.
  const mono = (spec.monoRanges ?? []).reduce((acc, r) => {
    const a = (r.startMs / 1000) * fps;
    const b = (r.endMs / 1000) * fps;
    const v = interpolate(frame, [a, a + 4, b - 4, b], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return Math.max(acc, v);
  }, 0);

  const mediaStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    scale: String(scale),
    // Purple Room: zoom from the bottom edge, so push-ins lift the face (more room under the chin) instead of lowering it
    transformOrigin: purple ? "50% 100%" : undefined,
    filter: `grayscale(${mono}) contrast(${1.05 + mono * 0.1}) saturate(${1.08 - mono})`,
  };

  return (
    <AbsoluteFill style={{ backgroundColor: colors.ink, overflow: "hidden" }}>
      {spec.footage.kind === "video" ? (
        <Video
          src={staticFile(spec.footage.src)}
          trimBefore={((spec.footage.trimBeforeMs ?? 0) / 1000) * fps}
          style={mediaStyle}
        />
      ) : (
        <Img src={staticFile(spec.footage.src)} style={mediaStyle} />
      )}
      {purple ? <SoftVignette /> : <Grade mono={mono} />}
    </AbsoluteFill>
  );
};

// Brand grade: cool shadows, warm skin stays natural, vignette, legibility gradient.
export const Grade: React.FC<{ mono?: number }> = ({ mono = 0 }) => (
  <>
    <AbsoluteFill style={{ background: colors.signalDeep, mixBlendMode: "soft-light", opacity: 0.22 * (1 - mono) }} />
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse 85% 70% at 50% 40%, transparent 55%, ${colors.ink}cc 100%)`,
      }}
    />
    <AbsoluteFill
      style={{
        background: `linear-gradient(to bottom, transparent 45%, ${colors.ink}99 85%, ${colors.ink}dd 100%)`,
      }}
    />
  </>
);

// Purple Room: the soft grade is applied by ffmpeg (skill 5.2). Only a light legibility gradient under the captions.
export const SoftVignette: React.FC = () => (
  <AbsoluteFill style={{ background: "linear-gradient(to bottom, transparent 55%, rgba(18,10,31,.35) 100%)" }} />
);
