import React from "react";
import { Composition, Folder, Still } from "remotion";
import { BrandBoard } from "./BrandBoard";
import { EditTemplate } from "./EditTemplate";
import { FPS, HORIZONTAL, VERTICAL } from "./brand/theme";
import type { EditSpec } from "./brand/types";
import brandDemo from "./videos/brand-demo/edit.json";
import aiAgent from "./videos/ai-agent/edit.json";
import codeVsNocode from "./videos/code-vs-nocode/edit.json";

// Register every video here: one line per video folder in src/videos/<slug>/edit.json
const videos: { id: string; spec: EditSpec }[] = [
  { id: "brand-demo", spec: brandDemo as EditSpec },
  { id: "ai-agent", spec: aiAgent as EditSpec },
  { id: "code-vs-nocode", spec: codeVsNocode as EditSpec },
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Still id="brand-board" component={BrandBoard} width={1920} height={1080} />
    <Folder name="videos">
      {videos.map(({ id, spec }) => {
        const size = spec.orientation === "vertical" ? VERTICAL : HORIZONTAL;
        return (
          <Composition
            key={id}
            id={id}
            component={EditTemplate}
            fps={FPS}
            width={size.width}
            height={size.height}
            durationInFrames={Math.ceil((spec.durationMs / 1000) * FPS)}
            defaultProps={{ spec }}
          />
        );
      })}
    </Folder>
    </>
  );
};
