import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';

/** Film grain: a pre-made noise tile (plan.grain_src, written by scripts/fx.py) shifted every frame. No SVG filters (they are slow on CPU). */
export const Grain: React.FC<{src?: string}> = ({src}) => {
  const frame = useCurrentFrame();
  if (!src) return null;
  const dx = (frame * 37) % 211;
  const dy = (frame * 91) % 173;
  return (
    <AbsoluteFill style={{opacity: 0.1, mixBlendMode: 'overlay', pointerEvents: 'none', overflow: 'hidden'}}>
      <Img src={staticFile(src)} style={{position: 'absolute', left: -dx, top: -dy, width: '130%', height: '130%', objectFit: 'cover'}} />
    </AbsoluteFill>
  );
};

/** Edge darkening with a plain radial gradient (no blur). strength 0..1. */
export const Vignette: React.FC<{strength: number}> = ({strength}) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,${(0.55 * Math.min(1, Math.max(0, strength))).toFixed(3)}) 100%)`,
    }}
  />
);
