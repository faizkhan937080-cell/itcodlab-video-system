import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** Large quote with author. props: text, author. */
export const Quote: React.FC<{text: string; author?: string; colors: Colors}> = ({text, author, colors}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  return (
    <AbsoluteFill style={{justifyContent: 'center', padding: 100 * u}}>
      <div style={{color: colors.coral, fontSize: 220 * u, fontWeight: 900, lineHeight: 0.6, opacity: easeOut(frame, 0, 12)}}>“</div>
      <div
        style={{
          color: colors.white,
          fontSize: 78 * u,
          fontWeight: 700,
          lineHeight: 1.2,
          opacity: easeOut(frame, 6, 24),
          transform: `translateY(${easeOut(frame, 6, 24, 30 * u, 0)}px)`,
        }}
      >
        {text}
      </div>
      {author ? <div style={{marginTop: 40 * u, color: colors.muted, fontSize: 48 * u, opacity: easeOut(frame, 20, 36)}}>— {author}</div> : null}
    </AbsoluteFill>
  );
};
