import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { fonts, plumBackground, purple } from "../../brand/theme";
import { EASE, lerp, useEnterExit, useProgress, useVY } from "./motion";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const useS = () => { const { width, height } = useVideoConfig(); return Math.min(width, height) / 1080; };

/** Full-screen plum stage. Captions move to the TOP during moments (PurpleCaptions handles it). */
const Stage: React.FC<{ durationInFrames: number; tag?: string; instant?: boolean; children: React.ReactNode }> = ({
  durationInFrames,
  tag = "ANIMATION",
  instant = false,
  children,
}) => {
  const s = useS();
  const ee = useEnterExit(durationInFrames, 0.35, 0.35, 0);
  const opacity = instant ? ee.exit : ee.opacity;
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

export type ShotKey = { t: number; zoom: number; fx: number; fy: number };
export type ShotHighlight = { t0: number; t1: number; x: number; y: number; w: number; h: number; label?: string; below?: boolean };
export type ShotCursor = { t0: number; t1: number; from: [number, number]; to: [number, number]; clickAt?: number };
export type ShotScan = { t0: number; t1: number; x: number; y: number; w: number; h: number; label?: string };
export type ShotChip = { t: number; x: number; y: number; text: string; dur?: number };

const easeIO = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const outBack = (x: number) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const win = (t: number, a: number, b: number, fade = 0.25) =>
  Math.max(0, Math.min(1, (t - a) / fade, (b - t) / fade));

/** Camera at time t (seconds): eased interpolation between keyframes. */
const camAt = (keys: ShotKey[], t: number): ShotKey => {
  if (t <= keys[0].t) return keys[0];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1], b = keys[i];
    if (t <= b.t) {
      const e = easeIO((t - a.t) / Math.max(0.001, b.t - a.t));
      return { t, zoom: lerp(e, a.zoom, b.zoom), fx: lerp(e, a.fx, b.fx), fy: lerp(e, a.fy, b.fy) };
    }
  }
  return keys[keys.length - 1];
};

/**
 * Full-screen real screenshot that is "alive": a camera that glides between keyframes (zoom + focus point),
 * spotlight highlights with a violet glow and a label, a moving cursor with a click ripple, a scan line,
 * chips that pop out, and a 3D tilt entrance. All positions are fractions of the IMAGE (0..1); times are
 * seconds from the overlay start. `aspect` = frame width/height; `imgAspect` = image width/height
 * (a tall image inside a wider frame scrolls).
 */
export const MomentShot: React.FC<{
  durationInFrames: number;
  src: string;
  aspect: number;
  imgAspect?: number;
  kicker?: string;
  kickerAt?: number;
  tag?: string;
  zoomTo?: number;
  focusFrom?: [number, number];
  focusTo?: [number, number];
  keys?: ShotKey[];
  highlights?: ShotHighlight[];
  cursor?: ShotCursor[];
  scan?: ShotScan[];
  chips?: ShotChip[];
  /** open directly on the screen (no fade/tilt), e.g. the very first frame of the video */
  instant?: boolean;
}> = ({ durationInFrames, src, aspect, imgAspect, kicker, kickerAt = 0.4, tag = "PLATFORM", zoomTo = 1.1, instant = false,
  focusFrom = [0.5, 0.5], focusTo, keys, highlights = [], cursor = [], scan = [], chips = [] }) => {
  const s = useS();
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const t = frame / fps;
  const dur = durationInFrames / fps;
  const horizontal = width > height;
  const maxW = width * (horizontal ? 0.84 : 0.88);
  const maxH = height * (horizontal ? 0.74 : 0.6);
  const boxW = Math.min(maxW, maxH * aspect);
  const boxH = boxW / aspect;
  const cy = height * (horizontal ? 0.565 : 0.55);
  // content = the image at the frame's width (taller than the frame when imgAspect < aspect)
  const cw = boxW;
  const ch = boxW / (imgAspect ?? aspect);
  const ks: ShotKey[] = keys && keys.length
    ? keys
    : [{ t: 0, zoom: 1, fx: focusFrom[0], fy: focusFrom[1] }, { t: dur, zoom: zoomTo, fx: (focusTo ?? focusFrom)[0], fy: (focusTo ?? focusFrom)[1] }];
  const cam = camAt(ks, t);
  const z = Math.max(1, cam.zoom);
  // put the focus point in the middle of the frame, but never show an empty edge
  const tx = Math.min(0, Math.max(boxW - z * cw, boxW / 2 - z * cam.fx * cw));
  const ty = Math.min(0, Math.max(boxH - z * ch, boxH / 2 - z * cam.fy * ch));

  // entrance: 3D tilt that settles, then a very slow float so the frame never feels frozen
  const enter = instant ? 1 : interpolate(t, [0, 0.75], [0, 1], { ...clamp, easing: EASE });
  const rx = (1 - enter) * 16 + Math.sin(t * 0.9) * 0.6;
  const ry = (1 - enter) * -12 + Math.sin(t * 0.6 + 1) * 0.9;
  const inv = 1 / z; // counter-scale for things that must keep their on-screen size
  const px = (v: number) => v * s * inv;

  const kick = kicker ? interpolate(t, [kickerAt, kickerAt + 0.45], [0, 1], { ...clamp, easing: outBack }) : 0;

  return (
    <Stage durationInFrames={durationInFrames} tag={tag} instant={instant}>
      <div style={{ position: "absolute", inset: 0, perspective: 1800 * s }}>
        <div
          style={{
            position: "absolute",
            left: (width - boxW) / 2,
            top: cy - boxH / 2,
            width: boxW,
            height: boxH,
            borderRadius: 20 * s,
            overflow: "hidden",
            border: `${Math.max(1, 1.5 * s)}px solid ${purple.cardBorder}`,
            boxShadow: `0 ${30 * s}px ${80 * s}px rgba(0,0,0,.55), 0 0 ${60 * s}px rgba(139,92,246,${0.18 * enter})`,
            opacity: Math.min(1, enter * 1.6),
            transform: `translateY(${(1 - enter) * 60 * s}px) rotateX(${rx}deg) rotateY(${ry}deg) scale(${0.9 + 0.1 * enter})`,
            background: "#fff",
          }}
        >
          <div style={{ position: "absolute", left: 0, top: 0, width: cw, height: ch, transformOrigin: "0 0",
            transform: `translate(${tx}px, ${ty}px) scale(${z})` }}>
            <Img src={staticFile(src)} style={{ width: cw, height: ch, display: "block" }} />

            {highlights.map((h, i) => {
              const a = win(t, h.t0, h.t1, 0.3);
              if (a <= 0) return null;
              const pop = outBack(Math.min(1, Math.max(0, (t - h.t0) / 0.45)));
              const pulse = 0.5 + 0.5 * Math.sin((t - h.t0) * 5);
              const L = h.x * cw, T = h.y * ch, W = h.w * cw, H = h.h * ch;
              return (
                <React.Fragment key={i}>
                  <div style={{ position: "absolute", left: L, top: T, width: W, height: H, borderRadius: px(12),
                    boxShadow: `0 0 0 ${9999}px rgba(18,10,31,${0.62 * a})`, pointerEvents: "none" }} />
                  <div style={{ position: "absolute", left: L, top: T, width: W, height: H, borderRadius: px(12),
                    border: `${px(4)}px solid ${purple.violet}`, opacity: a,
                    transform: `scale(${1.12 - 0.12 * pop})`,
                    boxShadow: `0 0 ${px(18 + 14 * pulse)}px ${purple.violet}, inset 0 0 ${px(14)}px rgba(139,92,246,.35)` }} />
                  {h.label ? (
                    <div style={{ position: "absolute", left: L + W / 2,
                      top: h.below ? T + H + px(16) : T - px(16),
                      transform: `translate(-50%, ${h.below ? 0 : -100}%) scale(${pop})`,
                      transformOrigin: h.below ? "50% 0" : "50% 100%", opacity: a,
                      whiteSpace: "nowrap", padding: `${px(10)}px ${px(22)}px`, borderRadius: 999,
                      background: purple.violet, color: purple.white, fontFamily: fonts.display, fontWeight: 800,
                      fontSize: px(32), letterSpacing: px(-0.5), boxShadow: `0 ${px(10)}px ${px(30)}px rgba(0,0,0,.45)` }}>
                      {h.label}
                    </div>
                  ) : null}
                </React.Fragment>
              );
            })}

            {scan.map((sc, i) => {
              const a = win(t, sc.t0, sc.t1 + 0.9, 0.2);
              if (a <= 0) return null;
              const L = sc.x * cw, T = sc.y * ch, W = sc.w * cw, H = sc.h * ch;
              const k = Math.min(1, Math.max(0, (t - sc.t0) / Math.max(0.1, sc.t1 - sc.t0)));
              const sweep = (Math.sin(k * Math.PI * 3 - Math.PI / 2) + 1) / 2; // down, up, down
              const done = interpolate(t, [sc.t1, sc.t1 + 0.35], [0, 1], { ...clamp, easing: outBack });
              const br = px(26);
              const corner = (pos: React.CSSProperties) => (
                <div style={{ position: "absolute", width: br, height: br, borderColor: done > 0 ? "#22C55E" : purple.violet,
                  borderStyle: "solid", borderWidth: 0, ...pos }} />
              );
              return (
                <div key={i} style={{ position: "absolute", left: L - px(12), top: T - px(12), width: W + px(24), height: H + px(24), opacity: a }}>
                  {corner({ left: 0, top: 0, borderLeftWidth: px(5), borderTopWidth: px(5) })}
                  {corner({ right: 0, top: 0, borderRightWidth: px(5), borderTopWidth: px(5) })}
                  {corner({ left: 0, bottom: 0, borderLeftWidth: px(5), borderBottomWidth: px(5) })}
                  {corner({ right: 0, bottom: 0, borderRightWidth: px(5), borderBottomWidth: px(5) })}
                  {done <= 0 ? (
                    <div style={{ position: "absolute", left: px(8), right: px(8), top: px(12) + sweep * H, height: px(4),
                      background: purple.lilac, boxShadow: `0 0 ${px(16)}px ${purple.violet}, 0 0 ${px(40)}px ${purple.violet}` }} />
                  ) : (
                    <div style={{ position: "absolute", left: "50%", top: "100%", transform: `translate(-50%, ${px(14)}px) scale(${done})`,
                      transformOrigin: "50% 0", whiteSpace: "nowrap", padding: `${px(10)}px ${px(22)}px`, borderRadius: 999,
                      background: "#22C55E", color: "#fff", fontFamily: fonts.display, fontWeight: 800, fontSize: px(30),
                      boxShadow: `0 ${px(10)}px ${px(30)}px rgba(0,0,0,.45)` }}>
                      {"✓ " + (sc.label ?? "verified")}
                    </div>
                  )}
                </div>
              );
            })}

            {chips.map((c, i) => {
              const d = c.dur ?? 1.4;
              const k = (t - c.t) / d;
              if (k < 0 || k > 1) return null;
              const pop = outBack(Math.min(1, k * d / 0.35));
              const fade = Math.min(1, (1 - k) * d / 0.3);
              return (
                <div key={i} style={{ position: "absolute", left: c.x * cw, top: c.y * ch - k * px(60),
                  transform: `translate(-50%, -50%) scale(${pop})`, opacity: fade, whiteSpace: "nowrap",
                  padding: `${px(10)}px ${px(20)}px`, borderRadius: 999, background: purple.plum, color: purple.white,
                  border: `${px(2)}px solid ${purple.violet}`, fontFamily: fonts.display, fontWeight: 800, fontSize: px(32),
                  boxShadow: `0 0 ${px(24)}px rgba(139,92,246,.6)` }}>
                  {c.text}
                </div>
              );
            })}

            {cursor.map((c, i) => {
              if (t < c.t0 - 0.2 || t > c.t1 + 0.6) return null;
              const k = easeIO(Math.min(1, Math.max(0, (t - c.t0) / Math.max(0.1, c.t1 - c.t0))));
              const x = lerp(k, c.from[0], c.to[0]) * cw;
              const y = lerp(k, c.from[1], c.to[1]) * ch;
              const appear = win(t, c.t0 - 0.2, c.t1 + 0.6, 0.2);
              const ca = c.clickAt ?? c.t1;
              const press = t >= ca && t < ca + 0.15 ? 0.82 : 1;
              const r = Math.max(0, Math.min(1, (t - ca) / 0.55));
              return (
                <React.Fragment key={i}>
                  {t >= ca && r < 1 ? (
                    <div style={{ position: "absolute", left: x, top: y, width: px(140), height: px(140), borderRadius: "50%",
                      transform: `translate(-50%, -50%) scale(${0.2 + r})`, border: `${px(5)}px solid ${purple.violet}`,
                      background: "rgba(139,92,246,.18)", opacity: 1 - r }} />
                  ) : null}
                  <svg width={px(46)} height={px(46)} viewBox="0 0 24 24"
                    style={{ position: "absolute", left: x - px(6), top: y - px(4), opacity: appear,
                      transform: `scale(${press})`, transformOrigin: "20% 15%",
                      filter: `drop-shadow(0 ${px(4)}px ${px(6)}px rgba(0,0,0,.45))` }}>
                    <path d="M4 2 L4 20 L9 15.5 L12.5 22.5 L15.5 21 L12 14 L19 14 Z" fill="#111" stroke="#fff" strokeWidth={1.6} strokeLinejoin="round" />
                  </svg>
                </React.Fragment>
              );
            })}
          </div>

          {kicker ? (
            <div style={{ position: "absolute", left: 22 * s, bottom: 22 * s, padding: `${10 * s}px ${20 * s}px`, borderRadius: 999,
              background: purple.violet, color: purple.white, fontFamily: fonts.display, fontWeight: 800, fontSize: 30 * s,
              letterSpacing: -0.5 * s, boxShadow: `0 ${10 * s}px ${30 * s}px rgba(0,0,0,.35)`,
              transform: `scale(${kick})`, transformOrigin: "0 100%" }}>
              {kicker}
            </div>
          ) : null}
        </div>
      </div>
    </Stage>
  );
};
