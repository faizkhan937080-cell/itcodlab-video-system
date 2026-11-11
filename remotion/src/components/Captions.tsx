import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {buildPages, CaptionDef, CaptionPage, CaptionStyle} from '../lib/captions';
import {insets} from '../lib/safe';
import {Colors} from '../lib/types';
import {CLEAN_FONT} from './Clean';

const Page: React.FC<{page: CaptionPage; style: CaptionStyle; colors: Colors}> = ({page, style, colors}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const safe = insets(width, height);
  const now = page.start_s + frame / fps;
  const pos = style.position ?? 'bottom';
  const hi = colors[style.highlight ?? 'coral'] ?? colors.coral;
  const justify = pos === 'top' ? 'flex-start' : pos === 'center' ? 'center' : 'flex-end';
  if (style.look === 'nt') {
    // neuraltech.ai: 1-3 word pages, bold white, spoken word heaviest, others lighter; pops in, cuts out on the next page.
    const k = easeOut(frame, 0, 4);
    const yt = (style.y_by_time ?? []).filter((z) => z.from_s <= page.start_s + 1e-6).pop();
    const y = yt?.y ?? style.y ?? 0.55;
    const size = 66 * (style.size ?? 1) * u;
    return (
      <AbsoluteFill>
        <div
          style={{
            position: 'absolute',
            left: 50 * u,
            right: 50 * u,
            top: y * height,
            transform: `translateY(-50%) scale(${0.92 + 0.08 * k})`,
            opacity: k,
            textAlign: 'center',
            fontFamily: CLEAN_FONT,
            fontSize: size,
            lineHeight: 1.2,
            color: '#FFFFFF',
            WebkitTextStroke: `${5 * u}px rgba(0,0,0,0.55)`,
            paintOrder: 'stroke fill',
          }}
        >
          {page.words.map((w, i) => {
            const active = w.start_s <= now && now < w.end_s;
            return (
              <span key={i} style={{display: 'inline-block', marginRight: 0.26 * size, fontWeight: active ? 800 : 600, opacity: active ? 1 : 0.82}}>
                {w.text}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>
    );
  }
  if (style.look === 'clean') {
    // Reference look (heysansser): big dark-grey bold words; the word being spoken is sharp, the next ones wait blurred and faint.
    const k = easeOut(frame, 0, 5);
    return (
      <AbsoluteFill>
        <div
          style={{
            position: 'absolute',
            left: 60 * u,
            right: 60 * u,
            top: (style.y ?? 0.68) * height,
            transform: `translateY(-50%) translateY(${(1 - k) * 18 * u}px)`,
            opacity: k,
            textAlign: 'center',
            fontFamily: CLEAN_FONT,
            fontWeight: 800,
            letterSpacing: -0.5 * u,
            fontSize: 76 * (style.size ?? 1) * u,
            lineHeight: 1.2,
            color: '#2A2E2C',
          }}
        >
          {page.words.map((w, i) => {
            const into = Math.min(1, Math.max(0, (now - w.start_s) * fps / 6)); // 0 = still to come, 1 = spoken (6 frames to sharpen)
            return (
              <span
                key={i}
                style={{
                  display: 'inline-block',
                  marginRight: 0.28 * 76 * (style.size ?? 1) * u,
                  opacity: 0.3 + 0.7 * into,
                  filter: `blur(${(1 - into) * 7 * u}px)`,
                }}
              >
                {w.text}
              </span>
            );
          })}
        </div>
      </AbsoluteFill>
    );
  }
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
