import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {popIn, unit} from '../lib/anim';

/** Emoji / short-text sticker that pops in with a wobble. props: text (emoji or word), x, y (0..1), size (0..1 of short side), rotate_deg. */
export const Sticker: React.FC<{text: string; x?: number; y?: number; size?: number; rotateDeg?: number}> = ({text, x, y, size, rotateDeg}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = unit(width, height);
  const pop = popIn(frame, fps);
  const wobble = Math.sin(frame / 3) * 3 * (1 - Math.min(1, frame / (fps * 0.8)));
  const px = (size ?? 0.3) * 1080 * u;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: `${(x ?? 0.5) * 100}%`,
          top: `${(y ?? 0.5) * 100}%`,
          fontSize: px,
          lineHeight: 1,
          transform: `translate(-50%, -50%) scale(${pop}) rotate(${(rotateDeg ?? -8) + wobble}deg)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
