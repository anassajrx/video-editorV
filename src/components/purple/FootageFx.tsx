import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, purple } from "../../brand/theme";
import { EASE, useEnterExit, useProgress } from "./motion";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Blur 0→6→0 px on the footage (0.9 s) + big serif chapter number under the chin. */
export const ChapterBlur: React.FC<{ top: number; durationInFrames: number; number: string; label?: string }> = ({
  top,
  durationInFrames,
  number,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const s = Math.min(width, height) / 1080;
  const blur = interpolate(frame, [0, 0.45 * fps, 0.9 * fps], [0, 6, 0], { ...clamp, easing: EASE });
  const dim = interpolate(frame, [0, 0.45 * fps, 0.9 * fps], [0, 0.25, 0], clamp);
  const { opacity, translateY } = useEnterExit(durationInFrames, 0.6, 0.4, 20);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ backdropFilter: `blur(${blur * 2 * s}px)`, background: `rgba(18,10,31,${dim})` }} />
      <div
        style={{
          position: "absolute",
          top: `${top * 100}%`,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity,
          transform: `translateY(${translateY * s}px)`,
        }}
      >
        <div style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 150 * s, lineHeight: 1, color: "#E6DEFF", textShadow: purple.captionShadow }}>
          {number}
        </div>
        {label ? (
          <div
            style={{
              fontFamily: fonts.arabic,
              fontWeight: 600,
              fontSize: 52 * s,
              color: purple.white,
              direction: "rtl",
              marginTop: 10 * s,
              textShadow: purple.captionShadow,
            }}
          >
            {label}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

/** The dead end: footage drains to B&W (0.4 s) and a word gets a violet strike-through (0.3 s). */
export const BWStrike: React.FC<{ top: number; durationInFrames: number; word: string; strikeAt?: number }> = ({
  top,
  durationInFrames,
  word,
  strikeAt = 0.5,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const s = Math.min(width, height) / 1080;
  const mono = interpolate(frame, [0, 0.4 * fps, durationInFrames - 0.4 * fps, durationInFrames], [0, 1, 1, 0], {
    ...clamp,
    easing: EASE,
  });
  const strike = useProgress(strikeAt, 0.3);
  const { opacity } = useEnterExit(durationInFrames, 0.4, 0.4, 0);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill style={{ backdropFilter: `grayscale(${mono}) contrast(${1 + 0.08 * mono})` }} />
      <div style={{ position: "absolute", top: `${top * 100}%`, left: 0, right: 0, textAlign: "center", opacity }}>
        <span
          style={{
            position: "relative",
            display: "inline-block",
            fontFamily: fonts.display,
            fontWeight: 800,
            fontSize: 104 * s,
            color: purple.white,
            letterSpacing: -2 * s,
            textShadow: purple.captionShadow,
          }}
        >
          {word}
          <span
            style={{
              position: "absolute",
              left: "-3%",
              top: "54%",
              height: 12 * s,
              width: `${106 * strike}%`,
              background: purple.violet,
              borderRadius: 6 * s,
            }}
          />
        </span>
      </div>
    </AbsoluteFill>
  );
};
