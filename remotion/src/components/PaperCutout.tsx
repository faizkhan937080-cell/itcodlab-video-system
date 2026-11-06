import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, popIn, unit} from '../lib/anim';
import {Colors} from '../lib/types';

// Deterministic pseudo-random (mulberry32) so every render frame draws the same torn edge.
const rng = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

/** Rectangle with a torn / jagged edge as a CSS clip-path polygon (percent points). */
export const tornPolygon = (seed: number, steps = 26, amp = 1.4): string => {
  const r = rng(seed);
  const j = () => (r() - 0.5) * 2 * amp;
  const pts: string[] = [];
  for (let i = 0; i <= steps; i++) pts.push(`${(i / steps) * 100}% ${Math.max(0, 1 + j())}%`);
  for (let i = 1; i <= steps; i++) pts.push(`${Math.min(100, 99 + j())}% ${(i / steps) * 100}%`);
  for (let i = steps - 1; i >= 0; i--) pts.push(`${(i / steps) * 100}% ${Math.min(100, 99 + j())}%`);
  for (let i = steps - 1; i >= 1; i--) pts.push(`${Math.max(0, 1 + j())}% ${(i / steps) * 100}%`);
  return `polygon(${pts.join(',')})`;
};

/** Photo as a torn-paper cutout with a white paper border, popping in with a stop-motion wobble.
 *  props: src (image in assets/), caption, rotate_deg (default -2), size (0.4-1, default 0.78), seed. No blur / shadow. */
export const PaperCutout: React.FC<{
  src: string;
  caption?: string;
  rotateDeg?: number;
  size?: number;
  seed?: number;
  colors: Colors;
}> = ({src, caption, rotateDeg = -2, size = 0.78, seed = 7, colors}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const wobble = Math.sin(Math.floor(frame / 3) * 1.7) * 0.8; // changes every 3rd frame = hand-made feel
  const s = 0.6 + 0.4 * Math.min(1, popIn(frame, fps));
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div
        style={{
          position: 'relative',
          width: `${size * 100}%`,
          height: `${size * 100}%`,
          transform: `rotate(${rotateDeg + wobble}deg) scale(${s})`,
          opacity: easeOut(frame, 0, 6),
        }}
      >
        <div style={{position: 'absolute', inset: 0, background: '#F4EFE6', clipPath: tornPolygon(seed)}} />
        <div style={{position: 'absolute', inset: '3.5%', clipPath: tornPolygon(seed + 11, 22, 1.8), overflow: 'hidden'}}>
          <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </div>
      </div>
      {caption ? (
        <div
          style={{
            position: 'absolute',
            bottom: 140 * u,
            left: 80 * u,
            right: 80 * u,
            textAlign: 'center',
            color: colors.white,
            fontSize: 60 * u,
            fontWeight: 800,
            WebkitTextStroke: `${6 * u}px ${colors.navy}`,
            paintOrder: 'stroke fill',
            opacity: easeOut(frame, 12, 24),
          }}
        >
          {caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
