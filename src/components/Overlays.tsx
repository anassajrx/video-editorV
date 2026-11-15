import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { colors, fonts, glow, type Accent } from "../brand/theme";
import type { Overlay } from "../brand/types";
import { clampTop } from "../brand/layout";
import { LineIcon } from "./Icons";

// All overlays are rendered inside a <Sequence>, so frame 0 = overlay start.

const usePop = (durationFrames: number) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const inP = spring({ frame, fps, config: { damping: 16, stiffness: 180, mass: 0.7 } });
  const out = interpolate(frame, [durationFrames - 8, durationFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return { p: inP * out, inP, frame, fps };
};

const accentHex = (a: Accent = "signal") => colors[a];

const Glass: React.FC<{ accent?: Accent; children: React.ReactNode; style?: React.CSSProperties; pulse?: number }> = ({
  accent = "signal",
  children,
  style,
  pulse = 1,
}) => {
  const hex = accentHex(accent);
  return (
    <div
      style={{
        background: `linear-gradient(160deg, ${colors.ink2}f2 0%, ${colors.ink}f2 100%)`,
        border: `2px solid ${hex}`,
        borderRadius: 36,
        boxShadow: `0 0 ${30 * pulse}px ${hex}88, 0 0 ${90 * pulse}px ${hex}33, inset 0 0 40px ${hex}22`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const Card: React.FC<Extract<Overlay, { type: "card" }> & { dur: number }> = (o) => {
  const { p, frame } = usePop(o.dur);
  const pulse = 1 + 0.15 * Math.sin(frame / 6);
  return (
    <div
      style={{
        position: "absolute",
        left: `${(o.x ?? 0.5) * 100}%`,
        top: `${o.y! * 100}%`,
        translate: "-50% 0",
        opacity: p,
        scale: String(interpolate(p, [0, 1], [0.82, 1])),
      }}
    >
      <Glass accent={o.accent} pulse={pulse} style={{ padding: "44px 64px", minWidth: 560, textAlign: "center" }}>
        {o.tag ? (
          <div style={{ fontFamily: fonts.mono, fontSize: 28, color: accentHex(o.accent), marginBottom: 14, letterSpacing: 2 }}>
            {o.tag}
          </div>
        ) : null}
        <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 64, color: colors.text, letterSpacing: -2, lineHeight: 1 }}>
          {o.title}
        </div>
        {o.subtitle ? (
          <div style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 48, color: colors.text, opacity: 0.85, marginTop: 10 }}>
            {o.subtitle}
          </div>
        ) : null}
      </Glass>
    </div>
  );
};

const Avatar: React.FC<{ src: string; size: number; ring?: string }> = ({ src, size, ring = colors.signal }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      padding: 5,
      background: `conic-gradient(${ring}, ${colors.signalDeep}, ${ring})`,
      boxShadow: glow(ring, 1.4),
    }}
  >
    <Img src={staticFile(src)} style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
  </div>
);

const Profile: React.FC<Extract<Overlay, { type: "profile" }> & { dur: number }> = (o) => {
  const { p, frame, fps } = usePop(o.dur);
  return (
    <div style={{ position: "absolute", left: "8%", top: `${o.y! * 100}%`, display: "flex", alignItems: "center", gap: 36, opacity: p }}>
      <div style={{ textAlign: "center", scale: String(interpolate(p, [0, 1], [0.6, 1])) }}>
        <Avatar src={o.avatar} size={190} />
        <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 44, color: colors.text, marginTop: 12 }}>{o.name}</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {o.lines.map((l, i) => {
          const lp = spring({ frame: frame - 8 - i * 6, fps, config: { damping: 20 } });
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, opacity: lp, translate: `${interpolate(lp, [0, 1], [-30, 0])}px 0` }}>
              <span style={{ fontFamily: fonts.mono, color: colors.signal, fontSize: 34, textShadow: glow(colors.signal, 0.6) }}>›</span>
              <span style={{ fontFamily: fonts.display, fontWeight: 600, fontSize: 36, color: colors.text }}>{l}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const Timeline: React.FC<Extract<Overlay, { type: "timeline" }> & { dur: number }> = (o) => {
  const { p, frame, fps } = usePop(o.dur);
  const n = o.steps.length;
  const pos = (i: number) => 10 + (80 * i) / Math.max(1, n - 1);
  const moveFrame = (((o.moveAtMs ?? o.startMs + 1200) - o.startMs) / 1000) * fps;
  const mv = spring({ frame: frame - moveFrame, fps, config: { damping: 22, stiffness: 120 } });
  const pinX = interpolate(mv, [0, 1], [pos(o.fromIndex), pos(o.toIndex)]);
  const lineP = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: `calc(${o.y! * 100}% + 150px)`, opacity: p }}>
      <div style={{ position: "absolute", left: "6%", width: `${88 * lineP}%`, height: 4, background: colors.line, borderRadius: 2 }} />
      <div style={{ position: "absolute", left: "6%", width: `${pinX - 6}%`, height: 4, background: colors.signal, boxShadow: glow(colors.signal), borderRadius: 2 }} />
      {o.steps.map((s, i) => (
        <div key={i} style={{ position: "absolute", left: `${pos(i)}%`, translate: "-50% 0", textAlign: "center" }}>
          <div style={{ width: 4, height: 26, background: colors.text, margin: "0 auto" }} />
          <div style={{ fontFamily: fonts.mono, fontSize: 30, color: pos(i) <= pinX + 0.5 ? colors.text : colors.muted, marginTop: 14, whiteSpace: "nowrap" }}>
            {s}
          </div>
        </div>
      ))}
      {o.avatar ? (
        <div style={{ position: "absolute", left: `${pinX}%`, top: -150, translate: "-50% 0" }}>
          <Avatar src={o.avatar} size={110} />
          <div style={{ width: 0, height: 0, margin: "0 auto", borderLeft: "14px solid transparent", borderRight: "14px solid transparent", borderTop: `18px solid ${colors.signal}` }} />
        </div>
      ) : null}
    </div>
  );
};

const Terminal: React.FC<Extract<Overlay, { type: "terminal" }> & { dur: number }> = (o) => {
  const { p, frame } = usePop(o.dur);
  const CHARS_PER_FRAME = 1.6;
  let budget = Math.max(0, frame - 6) * CHARS_PER_FRAME;
  const cursorOn = Math.floor(frame / 8) % 2 === 0;
  return (
    <div style={{ position: "absolute", left: "8%", right: "8%", top: `${o.y! * 100}%`, opacity: p, scale: String(interpolate(p, [0, 1], [0.9, 1])) }}>
      <Glass style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "20px 28px", borderBottom: `1px solid ${colors.line}` }}>
          {[colors.error, colors.ember, colors.success].map((c) => (
            <div key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c }} />
          ))}
          <div style={{ fontFamily: fonts.mono, color: colors.muted, fontSize: 26, marginLeft: 16 }}>{o.title ?? "~/projects"}</div>
        </div>
        <div style={{ padding: "28px 36px", fontFamily: fonts.mono, fontSize: 38, lineHeight: 1.5 }}>
          {o.lines.map((l, i) => {
            const shown = l.slice(0, Math.max(0, Math.floor(budget)));
            budget -= l.length + 6;
            if (shown.length === 0 && i > 0) return null;
            const isCmd = l.startsWith("$");
            const done = shown.length === l.length;
            return (
              <div key={i} style={{ color: isCmd ? colors.text : colors.signal, whiteSpace: "pre" }}>
                {shown}
                {!done && cursorOn ? <span style={{ background: colors.signal, color: colors.signal }}>_</span> : null}
              </div>
            );
          })}
        </div>
      </Glass>
    </div>
  );
};

const Stat: React.FC<Extract<Overlay, { type: "stat" }> & { dur: number }> = (o) => {
  const { p } = usePop(o.dur);
  const hex = accentHex(o.accent ?? "ember");
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: `${o.y! * 100}%`, textAlign: "center", opacity: p, scale: String(interpolate(p, [0, 1], [0.7, 1])) }}>
      <div style={{ fontFamily: fonts.display, fontWeight: 800, fontSize: 200, color: hex, textShadow: glow(hex, 1.5), letterSpacing: -8, lineHeight: 1 }}>{o.value}</div>
      <div style={{ fontFamily: fonts.mono, fontSize: 36, color: colors.text, letterSpacing: 4, marginTop: 8 }}>{o.label}</div>
    </div>
  );
};

const ImageCard: React.FC<Extract<Overlay, { type: "image" }> & { dur: number }> = (o) => {
  const { p } = usePop(o.dur);
  return (
    <div style={{ position: "absolute", left: "50%", top: `${o.y! * 100}%`, width: `${(o.width ?? 0.84) * 100}%`, translate: "-50% 0", opacity: p, scale: String(interpolate(p, [0, 1], [0.88, 1])) }}>
      <Glass style={{ padding: 10, overflow: "hidden" }}>
        <Img src={staticFile(o.src)} style={{ width: "100%", borderRadius: 28, display: "block" }} />
      </Glass>
    </div>
  );
};

// Small pop-up: glass circle + glowing line icon + optional mono label. Springs in with a tilt, floats gently.
const IconPop: React.FC<Extract<Overlay, { type: "icon" }> & { dur: number }> = (o) => {
  const { p, inP, frame } = usePop(o.dur);
  const hex = accentHex(o.accent);
  const float = Math.sin(frame / 14) * 5;
  const ring = interpolate(frame, [0, 18], [0, 1], { extrapolateRight: "clamp" });
  return (
    <div
      style={{
        position: "absolute",
        left: `${(o.x ?? 0.5) * 100}%`,
        top: `${o.y! * 100}%`,
        translate: `-50% ${float}px`,
        opacity: p,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 14,
      }}
    >
      <div style={{ position: "relative", scale: String(interpolate(inP, [0, 1], [0.4, 1])), rotate: `${interpolate(inP, [0, 1], [-14, 0])}deg` }}>
        {/* expanding ring on entry */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: `2px solid ${hex}`,
            scale: String(1 + ring * 0.5),
            opacity: 1 - ring,
          }}
        />
        <div
          style={{
            width: 150,
            height: 150,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: `radial-gradient(circle at 35% 30%, ${colors.ink2}f5, ${colors.ink}f5)`,
            border: `2px solid ${hex}`,
            boxShadow: `0 0 26px ${hex}77, 0 0 70px ${hex}2e, inset 0 0 30px ${hex}22`,
          }}
        >
          <LineIcon name={o.icon} size={78} color={hex} glowCss={`drop-shadow(0 0 8px ${hex}aa)`} />
        </div>
      </div>
      {o.label ? (
        <div
          style={{
            fontFamily: fonts.mono,
            fontWeight: 600,
            fontSize: 30,
            color: colors.text,
            letterSpacing: 1,
            padding: "6px 18px",
            borderRadius: 999,
            background: `${colors.ink}cc`,
            border: `1px solid ${colors.line}`,
            whiteSpace: "nowrap",
          }}
        >
          {o.label}
        </div>
      ) : null}
    </div>
  );
};

export const OverlayLayer: React.FC<{ overlay: Overlay; durationInFrames: number; minTop: number }> = ({ overlay: raw, durationInFrames, minTop }) => {
  const dur = durationInFrames;
  // y is the TOP edge; it can never go above minTop (below the face + caption band).
  const overlay = { ...raw, y: clampTop(raw.y, minTop) } as Overlay;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {overlay.type === "card" && <Card {...overlay} dur={dur} />}
      {overlay.type === "profile" && <Profile {...overlay} dur={dur} />}
      {overlay.type === "timeline" && <Timeline {...overlay} dur={dur} />}
      {overlay.type === "terminal" && <Terminal {...overlay} dur={dur} />}
      {overlay.type === "stat" && <Stat {...overlay} dur={dur} />}
      {overlay.type === "image" && <ImageCard {...overlay} dur={dur} />}
      {overlay.type === "icon" && <IconPop {...overlay} dur={dur} />}
    </AbsoluteFill>
  );
};
