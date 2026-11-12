import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {useIn} from './parts';
import {F, K, unit} from './theme';

type Card = {label: string; theme: 'dark' | 'grey' | 'light'; img?: string; lines?: string[]; at_s?: number};

/** Draft 1 / 2 / 3 phone cards (81.8-86.5 s): dark, grey (raised, middle), light; loop arrow "feedback -> next draft"
 * under them; an "Approved ✓" pill lands on the last card. */
export const RefDrafts: React.FC<{cards: Card[]; loop?: string; loop_s?: number; approved?: string; approved_s?: number}> = ({cards, loop, loop_s = 2, approved, approved_s}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const u = unit(width);
  const W = 0.29 * width;
  const H = 0.33 * height;
  const xs = [0.04, 0.355, 0.67];
  const ys = [0.33, 0.27, 0.33];
  const ap = useIn(approved_s ?? 1e6);
  const lp = interpolate(frame, [loop_s * fps, loop_s * fps + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <>
      <Page mode="full" />
      {cards.slice(0, 3).map((c, i) => (
        <CardView key={i} c={c} x={xs[i] * width} y={ys[i] * height} w={W} h={H} u={u} />
      ))}
      {loop ? (
        <div style={{position: 'absolute', left: 0.18 * width, right: 0.18 * width, top: 0.665 * height, height: 0.05 * height, borderBottom: `${2.5 * u}px solid #C9C5BC`, borderLeft: `${2.5 * u}px solid #C9C5BC`, borderRight: `${2.5 * u}px solid #C9C5BC`, borderRadius: `0 0 ${200 * u}px ${200 * u}px`, opacity: lp}}>
          <div style={{position: 'absolute', left: 0, right: 0, top: 0.012 * height, textAlign: 'center', fontFamily: F.ui, fontSize: 22 * u, color: K.grey}}>{loop}</div>
        </div>
      ) : null}
      {approved ? (
        <div style={{position: 'absolute', left: (0.67 + 0.1) * width, top: 0.625 * height, background: K.ink, color: '#fff', fontFamily: F.ui, fontWeight: 700, fontSize: 24 * u, padding: `${10 * u}px ${20 * u}px`, borderRadius: 14 * u, opacity: ap, transform: `scale(${0.8 + 0.2 * ap})`}}>{approved} ✓</div>
      ) : null}
    </>
  );
};

const CardView: React.FC<{c: Card; x: number; y: number; w: number; h: number; u: number}> = ({c, x, y, w, h, u}) => {
  const k = useIn(c.at_s ?? 0);
  const bg = c.theme === 'dark' ? '#1C1B19' : c.theme === 'grey' ? '#8E8C88' : '#F4F2EE';
  const ink = c.theme === 'light' ? K.ink : '#F4F2EE';
  return (
    <div style={{position: 'absolute', left: x, top: y, width: w, opacity: k}}>
      <div style={{height: h, borderRadius: 26 * u, background: bg, border: `${2.5 * u}px solid ${c.theme === 'light' ? '#2A2724' : '#2A2724'}`, overflow: 'hidden', position: 'relative'}}>
        {c.img ? <Img src={c.img.startsWith('http') ? c.img : staticFile(c.img)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', opacity: c.theme === 'grey' ? 0.55 : 0.9}} /> : null}
        <div style={{position: 'absolute', left: 22 * u, right: 18 * u, top: 0.3 * h, fontFamily: F.sans, color: ink}}>
          {(c.lines ?? []).map((l, i) => (
            <div key={i} style={{fontSize: (i === 0 ? 40 : 22) * u, fontWeight: i === 0 ? 800 : 500, opacity: i === 0 ? 1 : 0.75, marginTop: 8 * u}}>{l}</div>
          ))}
        </div>
      </div>
      <div style={{textAlign: 'center', marginTop: 18 * u, fontFamily: F.sans, fontWeight: 700, fontSize: 30 * u, color: K.ink}}>{c.label}</div>
    </div>
  );
};
