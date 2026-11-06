// Caption pages in the style of Remotion's createTikTokStyleCaptions: a few words per page, the spoken word is highlighted.
// Input is our transcript shape: segments {text, start_s, end_s} with optional words [{text, start_s, end_s}].
// Without word timings the words are spread evenly inside the segment (same rule as scripts/script_metrics.py).
export type CaptionWord = {text: string; start_s: number; end_s: number};
export type CaptionDef = {text: string; start_s: number; end_s: number; words?: CaptionWord[]};
export type CaptionStyle = {
  position?: 'bottom' | 'center' | 'top';
  max_words?: number;
  highlight?: string; // key of brand colors, default 'coral'
  size?: number; // 1 = default (72 px at 1080 short side)
};
export type CaptionPage = {start_s: number; end_s: number; words: CaptionWord[]};

const wordsOf = (c: CaptionDef): CaptionWord[] => {
  if (c.words && c.words.length) return c.words;
  const parts = c.text.split(/\s+/).filter(Boolean);
  const step = (c.end_s - c.start_s) / Math.max(1, parts.length);
  return parts.map((t, i) => ({text: t, start_s: c.start_s + i * step, end_s: c.start_s + (i + 1) * step}));
};

export const buildPages = (captions: CaptionDef[], maxWords: number): CaptionPage[] => {
  const n = Math.max(1, Math.floor(maxWords));
  const pages: CaptionPage[] = [];
  for (const c of captions) {
    const ws = wordsOf(c);
    for (let i = 0; i < ws.length; i += n) {
      const chunk = ws.slice(i, i + n);
      pages.push({start_s: chunk[0].start_s, end_s: chunk[chunk.length - 1].end_s, words: chunk});
    }
  }
  return pages.sort((a, b) => a.start_s - b.start_s);
};
