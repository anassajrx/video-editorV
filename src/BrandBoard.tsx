import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { colors, fonts, glow } from "./brand/theme";

const swatches: [string, string][] = [
  ["ink", colors.ink], ["ink2", colors.ink2], ["line", colors.line], ["text", colors.text], ["muted", colors.muted],
  ["signal", colors.signal], ["signalDeep", colors.signalDeep], ["ember", colors.ember], ["error", colors.error], ["success", colors.success],
];

export const BrandBoard: React.FC = () => (
  <AbsoluteFill style={{ background: colors.ink, padding: 80, color: colors.text, fontFamily: fonts.display, display: "flex", flexDirection: "row", gap: 80 }}>
    <div style={{ flex: 1.3, display: "flex", flexDirection: "column", gap: 44 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 36 }}>
        <Img src={staticFile("brand/mark.svg")} style={{ width: 150, height: 150 }} />
        <div>
          <div style={{ fontWeight: 800, fontSize: 84, letterSpacing: -3, lineHeight: 1 }}>YOUR NAME</div>
          <div style={{ fontFamily: fonts.mono, fontSize: 30, color: colors.muted, marginTop: 10 }}>// software engineer</div>
        </div>
      </div>
      <div style={{ fontSize: 52, lineHeight: 1.1 }}>
        <span style={{ fontWeight: 800, color: colors.signal, textShadow: glow(colors.signal) }}>Shipping</span>{" "}
        <span style={{ fontWeight: 500, fontSize: 34, color: colors.muted }}>code.</span>{" "}
        <span style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 64 }}>Explaining it</span>{" "}
        <span style={{ fontWeight: 800 }}>simply.</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
        {swatches.map(([n, h]) => (
          <div key={n}>
            <div style={{ height: 96, borderRadius: 18, background: h, border: `1px solid ${colors.line}`, boxShadow: ["signal", "ember"].includes(n) ? glow(h, 0.8) : undefined }} />
            <div style={{ fontFamily: fonts.mono, fontSize: 20, marginTop: 8 }}>{n}</div>
            <div style={{ fontFamily: fonts.mono, fontSize: 18, color: colors.muted }}>{h}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontWeight: 800, fontSize: 56, letterSpacing: -2 }}>Inter Tight — the engineer</div>
        <div style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 60 }}>Instrument Serif — the human</div>
        <div style={{ fontFamily: fonts.mono, fontSize: 40, color: colors.signal }}>JetBrains Mono — the code</div>
      </div>
    </div>
    <div style={{ flex: 1, position: "relative", borderRadius: 40, overflow: "hidden", border: `2px solid ${colors.line}` }}>
      <Img src={staticFile("brand/face-reference.png")} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 30%" }} />
      <AbsoluteFill style={{ background: colors.signalDeep, mixBlendMode: "soft-light", opacity: 0.25 }} />
      <AbsoluteFill style={{ background: `linear-gradient(to bottom, transparent 40%, ${colors.ink}ee 100%)` }} />
      <div style={{ position: "absolute", bottom: 60, left: 0, right: 0, textAlign: "center" }}>
        <span style={{ fontWeight: 500, fontSize: 34, color: colors.muted }}>now it </span>
        <span style={{ fontWeight: 700, fontSize: 56 }}>makes </span>
        <span style={{ fontWeight: 800, fontSize: 80, color: colors.ember, textShadow: glow(colors.ember, 0.8) }}>$2,000</span>
        <div style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 72 }}>a month</div>
      </div>
    </div>
  </AbsoluteFill>
);
