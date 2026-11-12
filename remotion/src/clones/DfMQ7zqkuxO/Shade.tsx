import React from 'react';
import {AbsoluteFill} from 'remotion';

/** Punch-in look (11.6, 27.3, 47.6-50.4, 80.5, 98.9 s): the face is lit and everything around it falls off to near
 * black (room in deep shadow). Overlay over the footage only (captions sit above it). cy = face centre height. */
export const RefShade: React.FC<{cy?: number; strength?: number}> = ({cy = 0.33, strength = 0.75}) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      background: `radial-gradient(ellipse 60% 55% at 50% ${cy * 100}%, rgba(8,7,6,0) 0%, rgba(8,7,6,0) 45%, rgba(8,7,6,${(strength * 0.7).toFixed(2)}) 80%, rgba(8,7,6,${strength.toFixed(2)}) 100%)`,
    }}
  />
);
