import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

export type BarItem = {label: string; value: number};

/** Horizontal bars growing in one after another. props: title, items [{label, value}], suffix. */
export const BarChart: React.FC<{title?: string; items: BarItem[]; suffix?: string; colors: Colors}> = ({
  title,
  items,
  suffix = '',
  colors,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <AbsoluteFill style={{justifyContent: 'center', padding: 90 * u}}>
      {title ? (
        <div style={{color: colors.white, fontSize: 80 * u, fontWeight: 800, marginBottom: 60 * u}}>{title}</div>
      ) : null}
      {items.map((it, i) => {
        const p = easeOut(frame, 6 + i * 8, 30 + i * 8);
        return (
          <div key={`${it.label}-${i}`} style={{marginBottom: 36 * u, opacity: Math.min(1, p * 2)}}>
            <div style={{display: 'flex', justifyContent: 'space-between', color: colors.white, fontSize: 48 * u, fontWeight: 700}}>
              <span>{it.label}</span>
              <span style={{color: colors.coral}}>
                {Math.round(it.value * p)}
                {suffix}
              </span>
            </div>
            <div style={{marginTop: 12 * u, height: 36 * u, background: colors.muted, opacity: 0.35, borderRadius: 18 * u}} />
            <div
              style={{
                marginTop: -36 * u,
                height: 36 * u,
                width: `${(it.value / max) * 100 * p}%`,
                background: colors.coral,
                borderRadius: 18 * u,
              }}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
