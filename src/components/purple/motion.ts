import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// Purple Room motion rules (skill 6.2): ease-in-out only, 0.5–0.9 s, no bounce, no springs.
export const EASE = Easing.inOut(Easing.cubic);

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Eased 0..1 between two times (seconds) relative to the current Sequence. */
export const useProgress = (startS: number, durS: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return interpolate(frame, [startS * fps, (startS + durS) * fps], [0, 1], { ...clamp, easing: EASE });
};

/** Enter (fade + rise) and exit (fade) envelope for an element living `durationInFrames`. */
export const useEnterExit = (durationInFrames: number, inS = 0.5, outS = 0.4, rise = 16) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = interpolate(frame, [0, inS * fps], [0, 1], { ...clamp, easing: EASE });
  const exit = interpolate(frame, [durationInFrames - outS * fps, durationInFrames], [1, 0], { ...clamp, easing: EASE });
  return {
    opacity: enter * exit,
    translateY: (1 - enter) * rise,
    enter,
    exit,
  };
};

export const lerp = (p: number, a: number, b: number) => a + (b - a) * p;

/** Vertical position for full-screen moments. Vertical (9:16): `p` of the height, as designed. Horizontal (16:9):
 * the same layout measured from the centre in px of the 1920-tall design, compressed to fit 1080 px. */
export const useVY = () => {
  const { width, height } = useVideoConfig();
  const s = Math.min(width, height) / 1080;
  if (height >= width) return (p: number) => `${p * 100}%`;
  const K = 0.8;
  return (p: number) => `calc(50% + ${((p - 0.5) * 1920 * s * K).toFixed(1)}px)`;
};
