import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, popIn, unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** A card with a soft 3D tilt (CSS perspective) and a shine sweep. */
export const Banner: React.FC<{headline: string; sub?: string; tag?: string; colors: Colors}> = ({
  headline,
  sub,
  tag,
  colors,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const u = unit(width, height);
  const s = popIn(frame, fps);
  const tilt = 14 - 28 * (frame / Math.max(1, durationInFrames));
  const shine = easeOut(frame, 6, 40, -40, 140);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', perspective: 1400 * u}}>
      <div
        style={{
          width: width * 0.8,
          padding: 70 * u,
          borderRadius: 40 * u,
          background: `linear-gradient(135deg, ${colors.coral}, #c23b40)`,
          boxShadow: `0 ${40 * u}px ${120 * u}px rgba(0,0,0,0.45)`,
          transform: `rotateY(${tilt}deg) rotateX(${tilt / 3}deg) scale(${0.85 + 0.15 * s})`,
          opacity: s,
          position: 'relative',
          overflow: 'hidden',
          color: colors.white,
        }}
      >
        {tag ? (
          <div style={{fontSize: 40 * u, letterSpacing: 6 * u, fontWeight: 700, opacity: 0.9}}>{tag.toUpperCase()}</div>
        ) : null}
        <div style={{fontSize: 104 * u, fontWeight: 800, lineHeight: 1.05, marginTop: 20 * u}}>{headline}</div>
        {sub ? <div style={{fontSize: 48 * u, marginTop: 30 * u, opacity: 0.95}}>{sub}</div> : null}
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: `${shine}%`,
            width: '18%',
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)',
            transform: 'skewX(-18deg)',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
