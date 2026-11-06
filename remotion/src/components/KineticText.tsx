import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {popIn, unit} from '../lib/anim';
import {fitFont} from '../lib/fit';
import {Colors} from '../lib/types';

/** Words pop in one by one. Words listed in `highlight` use the accent colour. */
export const KineticText: React.FC<{text: string; highlight?: string[]; colors: Colors}> = ({
  text,
  highlight = [],
  colors,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const size = fitFont({text, maxSize: 110 * u, boxW: width - 180 * u, boxH: height * 0.55, lineHeight: 1.25});
  const words = text.split(/\s+/).filter(Boolean);
  const hl = new Set(highlight.map((w) => w.toLowerCase()));
  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        padding: 90 * u,
        flexDirection: 'row',
        flexWrap: 'wrap',
        alignContent: 'center',
        gap: `${18 * u}px ${28 * u}px`,
      }}
    >
      {words.map((w, i) => {
        const p = popIn(frame, fps, i * 4);
        return (
          <span
            key={`${w}-${i}`}
            style={{
              display: 'inline-block',
              fontSize: size,
              fontWeight: 800,
              color: hl.has(w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '')) ? colors.coral : colors.white,
              opacity: p,
              transform: `translateY(${(1 - p) * 60 * u}px) scale(${0.85 + 0.15 * p})`,
            }}
          >
            {w}
          </span>
        );
      })}
    </AbsoluteFill>
  );
};
