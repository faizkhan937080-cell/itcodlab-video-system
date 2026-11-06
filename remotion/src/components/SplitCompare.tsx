import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

export type Side = {title: string; points?: string[]};

/** Two columns side by side. props: left {title, points[]}, right {title, points[]}. Stacks top/bottom in portrait. */
export const SplitCompare: React.FC<{left: Side; right: Side; colors: Colors}> = ({left, right, colors}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  const portrait = height >= width;
  const col = (side: Side, accent: string, delay: number) => {
    const p = easeOut(frame, delay, delay + 16);
    return (
      <div style={{flex: 1, padding: 50 * u, opacity: p, transform: `translateY(${(1 - p) * 40 * u}px)`}}>
        <div style={{color: accent, fontSize: 76 * u, fontWeight: 900, marginBottom: 28 * u}}>{side.title}</div>
        {(side.points ?? []).map((t, i) => (
          <div key={`${t}-${i}`} style={{color: colors.white, fontSize: 48 * u, fontWeight: 600, marginBottom: 20 * u, lineHeight: 1.2}}>
            • {t}
          </div>
        ))}
      </div>
    );
  };
  return (
    <AbsoluteFill style={{flexDirection: portrait ? 'column' : 'row', justifyContent: 'center', alignItems: 'stretch'}}>
      {col(left, colors.muted, 0)}
      <div
        style={{
          background: colors.coral,
          width: portrait ? '80%' : 8 * u,
          height: portrait ? 8 * u : '70%',
          alignSelf: 'center',
          opacity: easeOut(frame, 4, 14),
        }}
      />
      {col(right, colors.coral, 10)}
    </AbsoluteFill>
  );
};
