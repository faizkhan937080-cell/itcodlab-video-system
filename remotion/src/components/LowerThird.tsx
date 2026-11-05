import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

export const LowerThird: React.FC<{name: string; role?: string; colors: Colors}> = ({name, role, colors}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  const x = easeOut(frame, 0, 18, -width * 0.6, 0);
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', paddingBottom: 220 * u}}>
      <div
        style={{
          transform: `translateX(${x}px)`,
          marginLeft: 60 * u,
          padding: `${28 * u}px ${48 * u}px`,
          background: colors.navy,
          borderLeft: `${14 * u}px solid ${colors.coral}`,
          alignSelf: 'flex-start',
          boxShadow: `0 ${20 * u}px ${60 * u}px rgba(0,0,0,0.4)`,
        }}
      >
        <div style={{color: colors.white, fontSize: 68 * u, fontWeight: 800}}>{name}</div>
        {role ? <div style={{color: colors.muted, fontSize: 44 * u, marginTop: 6 * u}}>{role}</div> : null}
      </div>
    </AbsoluteFill>
  );
};
