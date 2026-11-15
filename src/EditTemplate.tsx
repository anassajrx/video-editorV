import React from "react";
import { AbsoluteFill, Sequence, staticFile, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import { Footage } from "./components/Footage";
import { KineticCaptions } from "./components/KineticCaptions";
import { OverlayLayer } from "./components/Overlays";
import type { EditSpec } from "./brand/types";
import { zones } from "./brand/layout";

// One template for every video. Each video is just an edit.json (EditSpec).
// qa=true hides the footage (pure black) so scripts/check_face.py can verify nothing is drawn in the face zone.
export const EditTemplate: React.FC<{ spec: EditSpec; qa?: boolean }> = ({ spec, qa }) => {
  const { fps } = useVideoConfig();
  const z = zones(spec);
  const f = (ms: number) => Math.round((ms / 1000) * fps);

  return (
    <AbsoluteFill>
      {qa ? <AbsoluteFill style={{ background: "#000" }} /> : <Footage spec={spec} />}

      {spec.overlays.map((o, i) => (
        <Sequence key={i} from={f(o.startMs)} durationInFrames={Math.max(1, f(o.endMs - o.startMs))} name={`${o.type} ${i}`}>
          <OverlayLayer overlay={o} minTop={z.overlayTop} durationInFrames={Math.max(1, f(o.endMs - o.startMs))} />
        </Sequence>
      ))}

      <KineticCaptions words={spec.captions} top={z.captionTop} />

      {spec.music ? <Audio src={staticFile(spec.music.src)} volume={spec.music.volume} /> : null}
      {(spec.sfx ?? []).map((s, i) => (
        <Sequence key={`sfx${i}`} from={f(s.atMs)} name={`sfx ${i}`}>
          <Audio src={staticFile(s.src)} volume={s.volume ?? 0.6} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
