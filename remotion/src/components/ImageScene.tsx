import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** Ken Burns zoom on an image from Drive assets/ (copied to remotion/public by the render script). */
export const ImageScene: React.FC<{src: string; caption?: string; colors: Colors}> = ({src, caption, colors}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const u = unit(width, height);
  const scale = 1 + 0.12 * easeOut(frame, 0, durationInFrames);
  return (
    <AbsoluteFill>
      <Img
        src={staticFile(src)}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}}
      />
      {caption ? (
        <div
          style={{
            position: 'absolute',
            left: 60 * u,
            right: 60 * u,
            bottom: 120 * u,
            padding: `${24 * u}px ${36 * u}px`,
            background: 'rgba(10,25,47,0.78)',
            color: colors.white,
            fontSize: 56 * u,
            fontWeight: 700,
            borderLeft: `${10 * u}px solid ${colors.coral}`,
            opacity: easeOut(frame, 10, 30),
          }}
        >
          {caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
