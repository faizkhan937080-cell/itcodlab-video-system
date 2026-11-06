import {measureText} from '@remotion/layout-utils';

const FAMILY = 'Inter, "Helvetica Neue", Arial, sans-serif';

/**
 * Largest font size (<= maxSize) at which `text` wraps inside boxW x boxH without a word sticking out.
 * Greedy word wrap with real text measurement; 8% safety margin because the final font may differ slightly.
 */
export const fitFont = (opts: {
  text: string;
  maxSize: number;
  boxW: number;
  boxH: number;
  fontWeight?: number;
  lineHeight?: number;
  minRatio?: number;
  fontFamily?: string;
}): number => {
  const {text, maxSize, boxW, boxH, fontWeight = 800, lineHeight = 1.05, minRatio = 0.4, fontFamily = FAMILY} = opts;
  const words = text.split(/\s+/).filter(Boolean);
  if (!words.length) return maxSize;
  const fits = (size: number): boolean => {
    const w = (t: string) => measureText({text: t, fontFamily, fontSize: size, fontWeight: String(fontWeight)}).width * 1.08;
    const space = w(' ');
    let lines = 1;
    let cur = 0;
    for (const word of words) {
      const ww = w(word);
      if (ww > boxW) return false;
      if (cur === 0) cur = ww;
      else if (cur + space + ww <= boxW) cur += space + ww;
      else {
        lines += 1;
        cur = ww;
      }
    }
    return lines * size * lineHeight <= boxH;
  };
  let lo = maxSize * minRatio;
  let hi = maxSize;
  if (fits(hi)) return hi;
  for (let i = 0; i < 12; i++) {
    const mid = (lo + hi) / 2;
    if (fits(mid)) lo = mid;
    else hi = mid;
  }
  return lo;
};
