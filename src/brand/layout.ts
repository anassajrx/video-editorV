import type { EditSpec } from "./types";

// Hard rule: nothing is ever drawn over or above the face.
// Captions start just under the chin; graphics start under the caption band.
export const CAPTION_BAND = 0.13; // height reserved for a 2-line caption page
export const BOTTOM_LIMIT = 0.94; // lowest point any element may reach

export const zones = (spec: EditSpec) => {
  const faceBottom = spec.faceZone?.bottom ?? 0.5;
  const captionTop = Math.max(spec.captionY ?? 0, faceBottom + 0.02);
  // Purple Room captions are 2 calm lines (~0.10 of the height)
  const overlayTop = captionTop + (spec.style === "purple" ? 0.1 : CAPTION_BAND);
  return { faceBottom, captionTop, overlayTop };
};

/** Clamp a requested top edge (0..1) so the element stays under the face. */
export const clampTop = (requested: number | undefined, minTop: number) =>
  Math.max(requested ?? minTop, minTop);
