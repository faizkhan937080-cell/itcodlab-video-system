// Top-left pixel HUD: fast-forward / rewind icon + "DAY n". Label blinks for 0.3 s when it changes.
import React from 'react';
import {loadFont} from '@remotion/google-fonts/PressStart2P';

const {fontFamily} = loadFont();
const tri = (x: number, dir: 1 | -1) => (dir > 0 ? `${x},0 ${x + 20},16 ${x},32` : `${x + 20},0 ${x},16 ${x + 20},32`);
export const DayIcon: React.FC<{kind: 'ff' | 'rewind'}> = ({kind}) => {
  const d = kind === 'ff' ? 1 : -1;
  return (
    <svg width={52} height={32} shapeRendering="crispEdges">
      <polygon points={tri(0, d)} fill="#fff" />
      <polygon points={tri(26, d)} fill="#fff" />
    </svg>
  );
};
export const DayCounter: React.FC<{label: string | null; icon: 'ff' | 'rewind' | null; sinceChangeS: number}> = ({label, icon, sinceChangeS}) => {
  const blinkOff = sinceChangeS >= 0 && sinceChangeS < 0.3 && Math.floor(sinceChangeS * 20) % 2 === 1;
  if (!icon && !label) return null;
  return (
    <div style={{position: 'absolute', left: 44, top: 68, display: 'flex', alignItems: 'center', gap: 22, fontFamily, color: '#fff', fontSize: 38, textShadow: '4px 4px 0 #000'}}>
      {icon ? <DayIcon kind={icon} /> : null}
      <span style={{opacity: blinkOff ? 0 : 1}}>{icon === 'rewind' ? '' : label ?? ''}</span>
    </div>
  );
};
export const PIXEL_FONT = fontFamily;
