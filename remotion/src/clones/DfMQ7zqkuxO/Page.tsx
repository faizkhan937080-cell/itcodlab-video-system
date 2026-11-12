import React from 'react';
import {AbsoluteFill, Img, staticFile, useVideoConfig} from 'remotion';
import {K} from './theme';

/** Cream page of the reference (full frame or top half). Optional real background picture for the bottom (dark room). */
export const Page: React.FC<{mode?: 'full' | 'split'; plate?: string; plateY?: number; plateScale?: number}> = ({mode = 'full', plate, plateY = 0.5, plateScale = 1}) => {
  const {height} = useVideoConfig();
  const top = mode === 'split' ? K.split * height : height;
  return (
    <AbsoluteFill style={{backgroundColor: K.dark}}>
      {mode === 'split' && plate ? (
        <div style={{position: 'absolute', left: 0, right: 0, top, bottom: 0, overflow: 'hidden'}}>
          <Img
            src={plate.startsWith('http') ? plate : staticFile(plate)}
            style={{position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', objectPosition: `50% ${plateY * 100}%`, transform: `scale(${plateScale})`}}
          />
        </div>
      ) : null}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: 0,
          height: top,
          background: `radial-gradient(ellipse 80% 60% at 50% 45%, ${K.pageLight} 0%, ${K.page} 70%, #E4E0D6 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};
