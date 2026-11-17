import React from "react";
import { AbsoluteFill, interpolate, Sequence, staticFile, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import { Footage } from "./components/Footage";
import { KineticCaptions } from "./components/KineticCaptions";
import { OverlayLayer } from "./components/Overlays";
import { isFootageFx, isFullScreen, isPurpleOverlay, PurpleCaptions, PurpleOverlayLayer } from "./components/purple";
import type { EditSpec, Overlay, PurpleOverlay } from "./brand/types";
import { zones } from "./brand/layout";

// One template for every video. Each video is just an edit.json (EditSpec).
// qa=true hides the footage (pure black) so scripts/check_face.py can verify nothing is drawn in the face zone.
// Layer order: footage → footage effects (blur, B&W) → under-chin cards → full-screen moments → captions.
export const EditTemplate: React.FC<{ spec: EditSpec; qa?: boolean }> = ({ spec, qa }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const z = zones(spec);
  const f = (ms: number) => Math.round((ms / 1000) * fps);
  const purpleStyle = spec.style === "purple";

  const layer = (o: Overlay | PurpleOverlay, i: number) => {
    const d = Math.max(1, f(o.endMs - o.startMs));
    return (
      <Sequence key={i} from={f(o.startMs)} durationInFrames={d} name={`${o.type} ${i}`}>
        {isPurpleOverlay(o) ? (
          <PurpleOverlayLayer overlay={o} durationInFrames={d} minTop={z.overlayTop} captionTop={z.captionTop} />
        ) : (
          <OverlayLayer overlay={o} minTop={z.overlayTop} durationInFrames={d} />
        )}
      </Sequence>
    );
  };
  const indexed = spec.overlays.map((o, i) => ({ o, i }));
  // clips are footage: hidden in QA renders, like the footage itself
  const fx = indexed.filter(({ o }) => isFootageFx(o) && !(qa && o.type === "clip"));
  const cards = indexed.filter(({ o }) => !isFootageFx(o) && !isFullScreen(o));
  const moments = indexed.filter(({ o }) => isFullScreen(o));

  return (
    <AbsoluteFill>
      {qa ? <AbsoluteFill style={{ background: "#000" }} /> : <Footage spec={spec} />}

      {fx.map(({ o, i }) => layer(o, i))}
      {cards.map(({ o, i }) => layer(o, i))}
      {moments.map(({ o, i }) => layer(o, i))}

      {purpleStyle ? (
        <PurpleCaptions
          words={spec.captions}
          top={z.captionTop}
          momentRanges={moments.map(({ o }) => ({ startMs: o.startMs, endMs: o.endMs }))}
        />
      ) : (
        <KineticCaptions words={spec.captions} top={z.captionTop} />
      )}

      {spec.music ? (
        <Audio
          src={staticFile(spec.music.src)}
          volume={(fr: number) => {
            const m = spec.music!;
            const fi = Math.max(1, f(m.fadeInMs ?? 0));
            const fo = Math.max(1, f(m.fadeOutMs ?? 0));
            return (
              m.volume *
              interpolate(fr, [0, fi], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) *
              interpolate(fr, [durationInFrames - fo, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
            );
          }}
        />
      ) : null}
      {(spec.sfx ?? []).map((s, i) => (
        <Sequence key={`sfx${i}`} from={f(s.atMs)} name={`sfx ${i}`}>
          <Audio src={staticFile(s.src)} volume={s.volume ?? 0.6} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
