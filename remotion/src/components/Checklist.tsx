import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, popIn, unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** Points appear one by one with a tick. props: title, items (string[]). */
export const Checklist: React.FC<{title?: string; items: string[]; colors: Colors}> = ({title, items, colors}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const u = unit(width, height);
  const step = Math.max(6, Math.floor((durationInFrames * 0.7) / Math.max(1, items.length)));
  return (
    <AbsoluteFill style={{justifyContent: 'center', padding: 90 * u}}>
      {title ? <div style={{color: colors.white, fontSize: 84 * u, fontWeight: 800, marginBottom: 56 * u}}>{title}</div> : null}
      {items.map((t, i) => {
        const at = 6 + i * step;
        const s = popIn(frame, fps, at);
        return (
          <div key={`${t}-${i}`} style={{display: 'flex', alignItems: 'center', marginBottom: 34 * u, opacity: easeOut(frame, at, at + 10)}}>
            <div
              style={{
                width: 72 * u,
                height: 72 * u,
                borderRadius: 36 * u,
                background: colors.coral,
                color: colors.white,
                fontSize: 48 * u,
                fontWeight: 900,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                transform: `scale(${0.5 + 0.5 * Math.min(1, s)})`,
                flexShrink: 0,
              }}
            >
              ✓
            </div>
            <div style={{marginLeft: 36 * u, color: colors.white, fontSize: 56 * u, fontWeight: 600, lineHeight: 1.15}}>{t}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
