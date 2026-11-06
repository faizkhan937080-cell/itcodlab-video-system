import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {popIn, unit} from '../lib/anim';
import {fitFont} from '../lib/fit';
import {Colors} from '../lib/types';

/** Classic meme caption: white bold text with a thick black outline, top or bottom. props: text, position ('top'|'bottom'|'center'), color. */
export const MemeText: React.FC<{text: string; position?: string; color?: string; colors: Colors}> = ({text, position, color, colors}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const size = fitFont({
    text: text.toUpperCase(), maxSize: 130 * u, boxW: width * 0.86, boxH: height * 0.22,
    fontWeight: 900, lineHeight: 1.05, fontFamily: 'Impact, "Arial Black", sans-serif',
  });
  const pop = popIn(frame, fps);
  const justify = position === 'top' ? 'flex-start' : position === 'center' ? 'center' : 'flex-end';
  return (
    <AbsoluteFill style={{justifyContent: justify, alignItems: 'center', padding: 60 * u}}>
      <div
        style={{
          fontFamily: 'Impact, "Arial Black", sans-serif',
          fontWeight: 900,
          fontSize: size,
          textTransform: 'uppercase',
          textAlign: 'center',
          lineHeight: 1.05,
          color: color ? colors[color] ?? color : '#fff',
          WebkitTextStroke: `${Math.max(4, size * 0.09)}px #000`,
          paintOrder: 'stroke fill',
          transform: `scale(${0.6 + 0.4 * pop})`,
          opacity: Math.min(1, pop * 2),
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
