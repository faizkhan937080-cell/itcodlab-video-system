import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, popIn, unit} from '../lib/anim';
import {Colors} from '../lib/types';

export const Title: React.FC<{text: string; subtitle?: string; colors: Colors}> = ({text, subtitle, colors}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const s = popIn(frame, fps);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: 80 * u, textAlign: 'center'}}>
      <div
        style={{
          color: colors.white,
          fontSize: 120 * u,
          fontWeight: 800,
          lineHeight: 1.05,
          transform: `scale(${0.8 + 0.2 * s})`,
          opacity: s,
        }}
      >
        {text}
      </div>
      <div
        style={{
          marginTop: 36 * u,
          height: 10 * u,
          width: 220 * u * easeOut(frame, 8, 28),
          background: colors.coral,
          borderRadius: 6 * u,
        }}
      />
      {subtitle ? (
        <div style={{marginTop: 36 * u, color: colors.muted, fontSize: 48 * u, opacity: easeOut(frame, 14, 34)}}>
          {subtitle}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
