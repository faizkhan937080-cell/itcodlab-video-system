// Thin pixel line from a structure to a capital label: the line draws first (6 frames), then the text types in (2 frames per letter).
import React from 'react';
import {S} from '../lib/pixel';
import {PIXEL_FONT} from './DayCounter';

export const Callout: React.FC<{text: string; ax: number; ay: number; sinceS: number; fps: number}> = ({text, ax, ay, sinceS, fps}) => {
  const fr = Math.floor(sinceS * fps);
  if (fr < 0) return null;
  const x0 = ax * S, y0 = ay * S;
  const x1 = x0 < 540 ? x0 + 190 : x0 - 190, y1 = Math.max(260, y0 - 190);
  const q = Math.min(1, (fr + 1) / 6);
  const n = Math.max(0, Math.min(text.length, Math.floor((fr - 6) / 2) + 1));
  const lx = x0 + (x1 - x0) * q, ly = y0 + (y1 - y0) * q;
  const shown = text.slice(0, n);
  return (
    <>
      <svg width={1080} height={1920} style={{position: 'absolute', left: 0, top: 0}} shapeRendering="crispEdges">
        <line x1={x0} y1={y0} x2={lx} y2={ly} stroke="#fff" strokeWidth={5} strokeDasharray="10 5" />
        <rect x={x0 - 8} y={y0 - 8} width={16} height={16} fill="#fff" />
      </svg>
      {n > 0 ? (
        <div style={{position: 'absolute', left: x1 < x0 ? x1 - shown.length * 30 - 10 : x1 + 10, top: y1 - 20, fontFamily: PIXEL_FONT, fontSize: 30, color: '#fff', textShadow: '4px 4px 0 #000', whiteSpace: 'nowrap'}}>{shown}</div>
      ) : null}
    </>
  );
};
