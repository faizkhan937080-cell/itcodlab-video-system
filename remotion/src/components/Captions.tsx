import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {buildPages, CaptionDef, CaptionPage, CaptionStyle} from '../lib/captions';
import {insets} from '../lib/safe';
import {Colors} from '../lib/types';

const Page: React.FC<{page: CaptionPage; style: CaptionStyle; colors: Colors}> = ({page, style, colors}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const safe = insets(width, height);
  const now = page.start_s + frame / fps;
  const pos = style.position ?? 'bottom';
  const hi = colors[style.highlight ?? 'coral'] ?? colors.coral;
  const justify = pos === 'top' ? 'flex-start' : pos === 'center' ? 'center' : 'flex-end';
  return (
    <AbsoluteFill
      style={{
        justifyContent: justify,
        alignItems: 'center',
        padding: pos === 'center' ? `0px ${Math.max(60 * u, safe.side)}px` : `${Math.max(220 * u, safe.top)}px ${Math.max(60 * u, safe.side)}px ${Math.max(220 * u, safe.bottom)}px`,
        opacity: easeOut(frame, 0, 4),
      }}
    >
      <div style={{textAlign: 'center', lineHeight: 1.15, fontWeight: 900, fontSize: 72 * (style.size ?? 1) * u}}>
        {page.words.map((w, i) => {
          const active = w.start_s <= now && now < w.end_s;
          return (
            <span
              key={i}
              style={{
                display: 'inline-block',
                marginRight: 16 * u,
                color: active ? hi : colors.white,
                transform: active ? 'scale(1.12)' : 'scale(1)',
                WebkitTextStroke: `${6 * u}px ${colors.navy}`,
                paintOrder: 'stroke fill',
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Word-by-word captions over the whole video. No blur or shadow: cheap on cloud renders. */
export const Captions: React.FC<{captions: CaptionDef[]; style?: CaptionStyle; colors: Colors}> = ({
  captions,
  style = {},
  colors,
}) => {
  const {fps} = useVideoConfig();
  const pages = buildPages(captions, style.max_words ?? 4);
  return (
    <>
      {pages.map((p, i) => {
        const next = pages[i + 1];
        const end = Math.min(next ? next.start_s : Infinity, p.end_s + 0.15);
        const from = Math.round(p.start_s * fps);
        const frames = Math.max(1, Math.round(end * fps) - from);
        return (
          <Sequence key={i} from={from} durationInFrames={frames}>
            <Page page={p} style={style} colors={colors} />
          </Sequence>
        );
      })}
    </>
  );
};
