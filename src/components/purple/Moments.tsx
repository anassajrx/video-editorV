import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, plumBackground, purple } from "../../brand/theme";
import { EASE, useEnterExit, useProgress, useVY } from "./motion";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const useS = () => { const { width, height } = useVideoConfig(); return Math.min(width, height) / 1080; };

/** Full-screen plum stage. Captions move to the TOP during moments (PurpleCaptions handles it). */
const Stage: React.FC<{ durationInFrames: number; tag?: string; children: React.ReactNode }> = ({
  durationInFrames,
  tag = "ANIMATION",
  children,
}) => {
  const s = useS();
  const { opacity } = useEnterExit(durationInFrames, 0.35, 0.35, 0);
  return (
    <AbsoluteFill style={{ background: plumBackground, opacity }}>
      {children}
      <div
        style={{
          position: "absolute",
          right: 40 * s,
          bottom: 40 * s,
          fontFamily: fonts.mono,
          fontSize: 18 * s,
          letterSpacing: 3 * s,
          color: purple.muted,
          border: `${Math.max(1, s)}px solid ${purple.dim2}`,
          borderRadius: 6 * s,
          padding: `${6 * s}px ${12 * s}px`,
        }}
      >
        {tag}
      </div>
    </AbsoluteFill>
  );
};

const Kicker: React.FC<{ text: string; top: number }> = ({ text, top: topP }) => {
  const s = useS();
  const top = useVY()(topP);
  return (
    <div
      style={{
        position: "absolute",
        top,
        left: 0,
        right: 0,
        textAlign: "center",
        fontFamily: fonts.mono,
        fontSize: 24 * s,
        letterSpacing: 8 * s,
        color: purple.muted,
        textTransform: "uppercase",
      }}
    >
      {text}
    </div>
  );
};

/** Blocks fall into a phone outline and stack; the last, light one drops in. */
export const MomentBlocks: React.FC<{ durationInFrames: number; label?: string }> = ({ durationInFrames, label = "NO CODE · DRAG & DROP" }) => {
  const s = useS();
  const vy = useVY();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const phoneW = 300 * s;
  const phoneH = 560 * s;
  const pad = 26 * s;
  const gap = 16 * s;
  const cell = (phoneW - pad * 2 - gap) / 2;
  // [x col, row from bottom, width cols, colour]
  const blocks: [number, number, number, string][] = [
    [0, 0, 2, purple.violet],
    [0, 1, 1, purple.dim2],
    [1, 1, 1, purple.dim2],
    [0, 2, 2, "#E9E3FF"],
  ];
  return (
    <Stage durationInFrames={durationInFrames}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: vy(0.52),
          width: phoneW,
          height: phoneH,
          transform: "translate(-50%, -50%)",
          border: `${4 * s}px solid ${purple.lilac}`,
          borderRadius: 48 * s,
          opacity: 0.95,
        }}
      >
        {blocks.map(([col, row, w, color], i) => {
          const start = (0.3 + i * 0.25) * fps;
          const p = interpolate(frame, [start, start + 0.6 * fps], [0, 1], { ...clamp, easing: EASE });
          const finalTop = phoneH - pad - (row + 1) * cell * 0.75 - row * gap;
          const y = interpolate(p, [0, 1], [-260 * s - row * 60 * s, finalTop]);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: pad + col * (cell + gap),
                top: y,
                width: w === 2 ? cell * 2 + gap : cell,
                height: cell * 0.75,
                borderRadius: 14 * s,
                background: color,
                opacity: p > 0 ? 1 : 0,
                transform: i === blocks.length - 1 ? `rotate(${(1 - p) * -12}deg)` : undefined,
              }}
            />
          );
        })}
      </div>
      <Kicker text={label} top={0.76} />
    </Stage>
  );
};

/** Rolling number (each step fades through) → big value + serif unit. */
export const MomentCounter: React.FC<{ durationInFrames: number; steps: number[]; value: string; unit: string; kicker?: string }> = ({
  durationInFrames,
  steps,
  value,
  unit,
  kicker,
}) => {
  const s = useS();
  const vy = useVY();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const stepsP = steps.map((_, i) =>
    interpolate(frame, [(0.2 + i * 0.25) * fps, (0.45 + i * 0.25) * fps], [0, 1], { ...clamp, easing: EASE }),
  );
  const landAt = 0.2 + steps.length * 0.25;
  const big = useProgress(landAt, 0.6);
  return (
    <Stage durationInFrames={durationInFrames}>
      {kicker ? <Kicker text={kicker} top={0.3} /> : null}
      <div
        style={{
          position: "absolute",
          top: vy(0.36),
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: fonts.display,
          fontWeight: 800,
          fontSize: 44 * s,
          color: purple.dim2,
          letterSpacing: -1 * s,
        }}
      >
        {steps.map((n, i) => (
          <span key={i} style={{ opacity: stepsP[i] * (1 - big * 0.4), margin: `0 ${14 * s}px` }}>
            {n.toLocaleString("en-US").replace(/,/g, " ")}
          </span>
        ))}
      </div>
      <div style={{ position: "absolute", top: vy(0.42), left: 0, right: 0, textAlign: "center", opacity: big }}>
        <div
          style={{
            fontFamily: fonts.display,
            fontWeight: 800,
            fontSize: 260 * s,
            lineHeight: 1,
            color: purple.white,
            letterSpacing: -10 * s,
            transform: `translateY(${(1 - big) * 30 * s}px) scale(${0.94 + 0.06 * big})`,
          }}
        >
          {value}
        </div>
        <div style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 76 * s, color: purple.lilac, marginTop: 10 * s }}>
          {unit}
        </div>
      </div>
    </Stage>
  );
};

/** One big slider: the knob glides (1.2 s) and the serif label writes itself. */
export const MomentSlider: React.FC<{ durationInFrames: number; label: string; kicker?: string; percent?: number }> = ({
  durationInFrames,
  label,
  kicker = "CUSTOM",
  percent = 68,
}) => {
  const s = useS();
  const vy = useVY();
  const knob = useProgress(0.3, 1.2);
  const write = useProgress(0.6, 1.2);
  const trackW = 640 * s;
  const pos = (percent / 100) * knob;
  return (
    <Stage durationInFrames={durationInFrames}>
      <div style={{ position: "absolute", top: vy(0.44), left: "50%", width: trackW, transform: "translateX(-50%)" }}>
        <div style={{ height: 14 * s, borderRadius: 7 * s, background: purple.dim }} />
        <div
          style={{ position: "absolute", top: 0, height: 14 * s, borderRadius: 7 * s, width: trackW * pos, background: purple.lilac }}
        />
        <div
          style={{
            position: "absolute",
            top: 7 * s,
            left: trackW * pos,
            width: 64 * s,
            height: 64 * s,
            borderRadius: "50%",
            background: purple.violet,
            transform: "translate(-50%, -50%)",
            boxShadow: `0 0 0 ${10 * s}px rgba(139,92,246,.18)`,
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          top: vy(0.51),
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: fonts.serif,
          fontStyle: "italic",
          fontSize: 96 * s,
          color: purple.white,
          clipPath: `inset(0 ${(1 - write) * 100}% 0 0)`,
        }}
      >
        {label}
      </div>
      <Kicker text={`${kicker} · ${Math.round(percent * knob)}%`} top={0.6} />
    </Stage>
  );
};

/** One line of code typing itself (40 ms/char), violet cursor, serif sub-line. */
export const MomentCode: React.FC<{ durationInFrames: number; code: string; sub?: string; file?: string }> = ({
  durationInFrames,
  code,
  sub,
  file = "besoin.ts",
}) => {
  const s = useS();
  const vy = useVY();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startF = 0.3 * fps;
  const chars = Math.max(0, Math.min(code.length, Math.floor((frame - startF) / (0.04 * fps))));
  const typed = code.slice(0, chars);
  const done = chars >= code.length;
  const blink = done ? Math.floor(frame / (0.5 * fps)) % 2 === 0 : true;
  const subP = useProgress(0.3 + code.length * 0.04 + 0.2, 0.7);
  // keyword colouring: first word white, rest lilac
  const sp = typed.indexOf(" ");
  return (
    <Stage durationInFrames={durationInFrames}>
      <Kicker text={file} top={0.34} />
      <div
        style={{
          position: "absolute",
          top: vy(0.42),
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: fonts.mono,
          fontSize: 76 * s,
          color: purple.white,
          whiteSpace: "pre",
        }}
      >
        {sp === -1 ? typed : typed.slice(0, sp)}
        <span style={{ color: purple.lilac }}>{sp === -1 ? "" : typed.slice(sp)}</span>
        <span
          style={{
            display: "inline-block",
            width: 6 * s,
            height: 80 * s,
            marginLeft: 6 * s,
            verticalAlign: "middle",
            background: purple.violet,
            opacity: blink ? 1 : 0,
          }}
        />
      </div>
      {sub ? (
        <div
          style={{
            position: "absolute",
            top: vy(0.51),
            left: 0,
            right: 0,
            textAlign: "center",
            fontFamily: fonts.serif,
            fontStyle: "italic",
            fontSize: 70 * s,
            color: purple.muted,
            opacity: subP,
            transform: `translateY(${(1 - subP) * 14 * s}px)`,
          }}
        >
          {sub}
        </div>
      ) : null}
    </Stage>
  );
};

/** Optional ending: serif line + handle on plum. */
export const PlumEndCard: React.FC<{ durationInFrames: number; line: string; handle: string }> = ({ durationInFrames, line, handle }) => {
  const s = useS();
  const vy = useVY();
  const p = useProgress(0.3, 0.8);
  const h = useProgress(0.8, 0.7);
  return (
    <Stage durationInFrames={durationInFrames} tag="END">
      <div
        style={{
          position: "absolute",
          top: vy(0.42),
          left: "8%",
          right: "8%",
          textAlign: "center",
          fontFamily: fonts.serif,
          fontStyle: "italic",
          fontSize: 96 * s,
          lineHeight: 1.1,
          color: purple.white,
          opacity: p,
          transform: `translateY(${(1 - p) * 20 * s}px)`,
        }}
      >
        {line}
      </div>
      <div
        style={{
          position: "absolute",
          top: vy(0.58),
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: fonts.mono,
          fontSize: 34 * s,
          letterSpacing: 2 * s,
          color: purple.lilac,
          opacity: h,
        }}
      >
        {handle}
      </div>
    </Stage>
  );
};

/** Words flowing down into each other: footage ↓ prompt ↓ video. (the last one in serif). */
export const MomentFlow: React.FC<{ durationInFrames: number; words: string[] }> = ({ durationInFrames, words }) => {
  const s = useS();
  const vy = useVY();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Stage durationInFrames={durationInFrames}>
      <div style={{ position: "absolute", top: vy(0.38), left: 0, right: 0, textAlign: "center" }}>
        {words.map((w, i) => {
          const at = 0.3 + i * 0.6;
          const p = interpolate(frame, [at * fps, (at + 0.6) * fps], [0, 1], { ...clamp, easing: EASE });
          const last = i === words.length - 1;
          const active = interpolate(frame, [(at + 0.6) * fps, (at + 0.9) * fps], [1, 0.45], clamp);
          return (
            <div key={i} style={{ opacity: p }}>
              {i > 0 ? (
                <div style={{ fontFamily: fonts.mono, fontSize: 40 * s, color: purple.violet, lineHeight: 1.4 }}>↓</div>
              ) : null}
              <div
                style={{
                  fontFamily: last ? fonts.serif : fonts.mono,
                  fontStyle: last ? "italic" : "normal",
                  fontSize: (last ? 110 : 58) * s,
                  color: last ? purple.white : purple.lilac,
                  opacity: last ? 1 : active,
                  transform: `translateY(${(1 - p) * -30 * s}px)`,
                  lineHeight: 1.2,
                }}
              >
                {w}
              </div>
            </div>
          );
        })}
      </div>
    </Stage>
  );
};

/** End card: serif kicker + big mono word with a blinking violet cursor + small line. */
export const CtaEndCard: React.FC<{ durationInFrames: number; kicker: string; word: string; sub?: string }> = ({
  durationInFrames,
  kicker,
  word,
  sub,
}) => {
  const s = useS();
  const vy = useVY();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = useProgress(0.2, 0.7);
  const typed = Math.max(0, Math.min(word.length, Math.floor((frame - 0.7 * fps) / (0.08 * fps))));
  const blink = Math.floor(frame / (0.5 * fps)) % 2 === 0;
  const subP = useProgress(1.3, 0.6);
  return (
    <Stage durationInFrames={durationInFrames} tag="END">
      <div style={{ position: "absolute", top: vy(0.38), left: 0, right: 0, textAlign: "center", opacity: p }}>
        <div style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 120 * s, color: purple.white, lineHeight: 1.1 }}>{kicker}</div>
        <div style={{ fontFamily: fonts.mono, fontSize: 120 * s, color: purple.white, marginTop: 10 * s }}>
          {word.slice(0, typed)}
          <span
            style={{
              display: "inline-block",
              width: 12 * s,
              height: 120 * s,
              marginLeft: 10 * s,
              verticalAlign: "middle",
              background: purple.violet,
              opacity: blink ? 1 : 0,
            }}
          />
        </div>
        {sub ? (
          <div style={{ fontFamily: fonts.display, fontWeight: 500, fontSize: 36 * s, color: purple.muted, marginTop: 30 * s, opacity: subP }}>
            {sub}
          </div>
        ) : null}
      </div>
    </Stage>
  );
};
