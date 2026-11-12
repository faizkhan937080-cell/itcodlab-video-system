import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {EXT} from '../ext';
import {FONTS} from '../ext/fonts';
import {CaptionDef, CaptionStyle} from '../lib/captions';

/** Clone mode captions: an OUTSIDE caption component (remocn caption-*), fed word timings in @remotion/captions
 * format, in a Google font. Position (y, as a fraction of height) and props come from the plan. */
export const ExtCaptions: React.FC<{captions: CaptionDef[]; style: CaptionStyle & Record<string, any>}> = ({captions, style}) => {
  const {height} = useVideoConfig();
  const C = EXT[style.component ?? ''];
  if (!C) throw new Error(`caption component ${style.component} not in ext/REGISTRY`);
  const caps = captions.flatMap((c) =>
    (c.words && c.words.length ? c.words : [{text: c.text, start_s: c.start_s, end_s: c.end_s}]).map((w, i) => ({
      text: (i === 0 ? '' : ' ') + w.text,
      startMs: Math.round(w.start_s * 1000),
      endMs: Math.round(w.end_s * 1000),
      timestampMs: Math.round(((w.start_s + w.end_s) / 2) * 1000),
      confidence: 1,
    })),
  );
  const yBy = (style.y_by_time ?? []) as {from_s: number; y: number}[];
  const family = style.font ? FONTS[style.font] : undefined;
  return (
    <AbsoluteFill style={{fontFamily: family}}>
      <YBox yBy={yBy} y={style.y ?? 0.55} height={height}>
        <C captions={caps} {...(style.props ?? {})} />
      </YBox>
    </AbsoluteFill>
  );
};

const YBox: React.FC<{yBy: {from_s: number; y: number}[]; y: number; height: number; children: React.ReactNode}> = ({yBy, y, height, children}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const t = frame / fps;
  const cur = yBy.filter((z) => z.from_s <= t + 1e-6).pop()?.y ?? y;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: cur * height, transform: 'translateY(-50%)', display: 'flex', justifyContent: 'center'}}>
      {children}
    </div>
  );
};
