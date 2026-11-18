import React from "react";
import { Composition, Folder } from "remotion";
import { EditTemplate } from "./EditTemplate";
import { FPS, HORIZONTAL, VERTICAL } from "./brand/theme";
import type { EditSpec } from "./brand/types";
import brandDemo from "./videos/brand-demo/edit.json";
import purpleDemo from "./videos/purple-demo/edit.json";
import comeback from "./videos/comeback/edit.json";
import myVideo from "./videos/my-video/edit.json";

// Register every video here: one line per video folder in src/videos/<slug>/edit.json
const videos: { id: string; spec: EditSpec }[] = [
  { id: "brand-demo", spec: brandDemo as EditSpec },
  { id: "purple-demo", spec: purpleDemo as EditSpec },
  { id: "comeback", spec: comeback as EditSpec },
  { id: "my-video", spec: myVideo as EditSpec },
];

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
