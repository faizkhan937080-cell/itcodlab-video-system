import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, popIn, unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** Big number that counts up. props: value, prefix, suffix, decimals, label. */
export const Counter: React.FC<{
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  label?: string;
  colors: Colors;
}> = ({value, prefix = '', suffix = '', decimals = 0, label, colors}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames, width, height} = useVideoConfig();
  const u = unit(width, height);
  const n = value * easeOut(frame, 0, Math.max(8, Math.round(durationInFrames * 0.6)));
  const s = popIn(frame, fps);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: 80 * u}}>
      <div style={{color: colors.coral, fontSize: 260 * u, fontWeight: 900, lineHeight: 1, opacity: s}}>
        {prefix}
        {n.toFixed(decimals)}
        {suffix}
      </div>
      {label ? (
        <div style={{marginTop: 40 * u, color: colors.white, fontSize: 64 * u, fontWeight: 700, opacity: easeOut(frame, 10, 30)}}>
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
