import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {F, K, unit} from './theme';

/** "Step 1 Set it up": grey regular step number + charcoal bold title, centred at 4 % height (12.5-54 s). */
export const StepHeader: React.FC<{step: string; title: string}> = ({step, title}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, right: 0, top: K.headerY * height, transform: 'translateY(-50%)', textAlign: 'center', fontFamily: F.sans, fontSize: 36 * u, letterSpacing: -0.3 * u}}>
        <span style={{color: K.grey, fontWeight: 500, marginRight: 10 * u}}>{step}</span>
        <span style={{color: K.ink, fontWeight: 700}}>{title}</span>
      </div>
    </AbsoluteFill>
  );
};
