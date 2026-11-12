import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {K} from './theme';

/** Full-frame real background (dark room) behind the keyed talking head: full shot / punch-in layouts. */
export const RefPlate: React.FC<{src: string; y?: number; scale?: number}> = ({src, y = 0.5, scale = 1}) => (
  <AbsoluteFill style={{backgroundColor: K.dark, overflow: 'hidden'}}>
    <Img src={src.startsWith('http') ? src : staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `50% ${y * 100}%`, transform: `scale(${scale})`}} />
  </AbsoluteFill>
);
