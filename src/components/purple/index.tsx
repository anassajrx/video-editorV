import React from "react";
import { FULL_SCREEN_TYPES, type Overlay, type PurpleOverlay } from "../../brand/types";
import { clampTop } from "../../brand/layout";
import { ChapterChip, CommentCard, GapBars, PinnedReply } from "./Cards";
import { BWStrike, ChapterBlur } from "./FootageFx";
import { CtaEndCard, MomentBlocks, MomentCode, MomentCounter, MomentFlow, MomentSlider, PlumEndCard } from "./Moments";
import { CreditRows, FileStack, ProgressCard } from "./Cards2";
import { AbsoluteFill, staticFile } from "remotion";
import { Video } from "@remotion/media";

export { PurpleCaptions } from "./PurpleCaptions";
export { FrostedCard } from "./FrostedCard";
export { CommentCard, ChapterChip, GapBars, PinnedReply, ChapterBlur, BWStrike };
export { MomentBlocks, MomentCounter, MomentSlider, MomentCode, MomentFlow, PlumEndCard, CtaEndCard };
export { FileStack, ProgressCard, CreditRows };

const PURPLE_TYPES = new Set<string>([
  "comment",
  "chapterChip",
  "gapBars",
  "pinnedReply",
  "chapterBlur",
  "bwStrike",
  "fileStack",
  "progressCard",
  "creditRows",
  "clip",
  ...FULL_SCREEN_TYPES,
]);

export const isPurpleOverlay = (o: Overlay | PurpleOverlay): o is PurpleOverlay => PURPLE_TYPES.has(o.type);
export const isFullScreen = (o: Overlay | PurpleOverlay) => (FULL_SCREEN_TYPES as readonly string[]).includes(o.type);

/** Footage effects sit under captions and cards. */
export const isFootageFx = (o: Overlay | PurpleOverlay) => o.type === "chapterBlur" || o.type === "bwStrike" || o.type === "clip";

/**
 * Renders one Purple Room overlay inside its <Sequence> (frame 0 = overlay start).
 * `captionTop` = top of the caption band (under the chin); `minTop` = top of the card zone (under the captions).
 */
export const PurpleOverlayLayer: React.FC<{
  overlay: PurpleOverlay;
  durationInFrames: number;
  minTop: number;
  captionTop: number;
}> = ({ overlay: o, durationInFrames: d, minTop, captionTop }) => {
  switch (o.type) {
    case "comment":
      return <CommentCard top={clampTop(o.y, minTop)} durationInFrames={d} text={o.text} likes={o.likes} likesFrom={o.likesFrom} />;
    case "chapterChip":
      return <ChapterChip top={clampTop(o.y, minTop)} durationInFrames={d} number={o.number} label={o.label} />;
    case "gapBars":
      return <GapBars top={clampTop(o.y, minTop)} durationInFrames={d} a={o.a} b={o.b} />;
    case "pinnedReply":
      return <PinnedReply top={clampTop(o.y, minTop)} durationInFrames={d} comment={o.comment} reply={o.reply} />;
    case "chapterBlur":
      // the serif number sits under the captions (captions keep their band)
      return <ChapterBlur top={minTop} durationInFrames={d} number={o.number} label={o.label} />;
    case "bwStrike":
      return (
        <BWStrike
          top={captionTop + 0.115}
          durationInFrames={d}
          word={o.word}
          strikeAt={o.strikeAtMs !== undefined ? (o.strikeAtMs - o.startMs) / 1000 : undefined}
        />
      );
    case "momentBlocks":
      return <MomentBlocks durationInFrames={d} label={o.label} />;
    case "momentCounter":
      return <MomentCounter durationInFrames={d} steps={o.steps} value={o.value} unit={o.unit} kicker={o.kicker} />;
    case "momentSlider":
      return <MomentSlider durationInFrames={d} label={o.label} kicker={o.kicker} percent={o.percent} />;
    case "momentCode":
      return <MomentCode durationInFrames={d} code={o.code} sub={o.sub} file={o.file} />;
    case "endCard":
      return <PlumEndCard durationInFrames={d} line={o.line} handle={o.handle} />;
    case "fileStack":
      return <FileStack top={clampTop(o.y, minTop)} durationInFrames={d} lines={o.lines} every={o.every} />;
    case "progressCard":
      return <ProgressCard top={clampTop(o.y, minTop)} durationInFrames={d} label={o.label} from={o.from} to={o.to} />;
    case "creditRows":
      return <CreditRows top={clampTop(o.y, minTop)} durationInFrames={d} rows={o.rows} who={o.who} every={o.every} />;
    case "momentFlow":
      return <MomentFlow durationInFrames={d} words={o.words} />;
    case "ctaEndCard":
      return <CtaEndCard durationInFrames={d} kicker={o.kicker} word={o.word} sub={o.sub} />;
    case "clip":
      return (
        <AbsoluteFill>
          <Video src={staticFile(o.src)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        </AbsoluteFill>
      );
  }
};
