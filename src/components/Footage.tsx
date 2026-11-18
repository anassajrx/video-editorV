import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { colors, plumBackground } from "../brand/theme";
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

  // Split screen: the footage glides into a rounded panel on the left (the face stays fully visible, nothing over it)
  // while a screen is shown on the right (splitShot overlay). Panel = SPLIT geometry (fractions of the frame).
  const { width: W, height: H } = useVideoConfig();
  const sp = (spec.split ?? []).reduce((acc, r) => {
    const a = (r.startMs / 1000) * fps;
    const b = (r.endMs / 1000) * fps;
    const tr = 0.55 * fps;
    const v = interpolate(frame, [a, a + tr, b - tr, b], [0, 1, 1, 0], {
      extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
    return Math.max(acc, v);
  }, 0);
  const k = 1 - (1 - SPLIT.scale) * sp;
  const panel: React.CSSProperties = {
    position: "absolute", left: 0, top: 0, width: W, height: H, overflow: "hidden",
    transformOrigin: "0 0",
    transform: `translate(${SPLIT.left * W * sp}px, ${SPLIT.top * H * sp}px) scale(${k})`,
    borderRadius: (28 * sp) / k,
    boxShadow: sp > 0 ? `0 ${40 * sp}px ${100 * sp}px rgba(0,0,0,${0.55 * sp}), 0 0 0 ${2 / k}px rgba(196,181,253,${0.3 * sp})` : undefined,
  };

  const mediaStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    scale: String(scale),
    // Purple Room: zoom from the bottom edge (vertical: more room under the chin). `pushOrigin` overrides it, e.g.
    // "50% 0%" when the head is close to the top of the frame (push-ins then never crop the head).
    transformOrigin: spec.pushOrigin ?? (purple ? "50% 100%" : undefined),
    filter: `grayscale(${mono}) contrast(${1.05 + mono * 0.1}) saturate(${1.08 - mono})`,
  };

  return (
    <AbsoluteFill style={{ backgroundColor: colors.ink, overflow: "hidden" }}>
      {sp > 0 ? <AbsoluteFill style={{ background: plumBackground, opacity: Math.min(1, sp * 2) }} /> : null}
      <div style={panel}>
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
      </div>
    </AbsoluteFill>
  );
};

/** Split-screen panel of the footage: scale and top-left corner, as fractions of the frame. */
export const SPLIT = { scale: 0.5, left: 0.03, top: 0.08 };

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
