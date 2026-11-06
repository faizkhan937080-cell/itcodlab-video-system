// Instagram Reels safe zones for 9:16 (same numbers as config/limits.json -> safezone.strict; a test keeps them equal).
export const SAFE = {top: 0.14, bottom: 0.35, side: 0.06};
const LANDSCAPE_MARGIN = 0.05;

export type Insets = {top: number; bottom: number; side: number};

/** Margins in px. Portrait (>= 1.5:1) gets the Reels zones, everything else a plain title-safe margin. */
export const insets = (width: number, height: number): Insets =>
  height / width >= 1.5
    ? {top: height * SAFE.top, bottom: height * SAFE.bottom, side: width * SAFE.side}
    : {top: height * LANDSCAPE_MARGIN, bottom: height * LANDSCAPE_MARGIN, side: width * LANDSCAPE_MARGIN};
