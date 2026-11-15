// Blood-donation explainer shots, same drawn anatomy look as BodyShots. Deterministic, no state.
// Art area (after the 1.12 zoom in BodyScene) is design x 120..960, y 0..880.
import React from 'react';
import {random} from 'remotion';
import {C, FONT, ramp, lerp} from './MedScene';
import {B} from './BodyScene';
import type {BodyProps} from './BodyScene';

const YEL = C.arrow;
const BLOOD0 = '#C8242B', BLOOD1 = '#7E1218', PLASMA = '#F2C75A', WATER = '#8FD3FF', EPO = '#C58BF0';
const txt = (x: number, y: number, s: string, size: number, fill = '#F3DCC2', anchor: 'start' | 'middle' | 'end' = 'middle', w = 800) => (
  <text x={x} y={y} textAnchor={anchor} fontFamily={FONT} fontWeight={w} fontSize={size} fill={fill} stroke="#120D0E" strokeWidth={size * 0.16} style={{paintOrder: 'stroke'}}>{s}</text>
);
const ease = (q: number) => 1 - (1 - Math.min(1, Math.max(0, q))) ** 3;

/** A red blood cell disc (side view): biconcave look from two ellipses. */
const Rbc: React.FC<{x: number; y: number; r?: number; rot?: number; o?: number}> = ({x, y, r = 22, rot = 0, o = 1}) => (
  <g transform={`translate(${x} ${y}) rotate(${rot})`} opacity={o}>
    <ellipse rx={r} ry={r * 0.72} fill={BLOOD0} stroke="#FF8A7A" strokeWidth={2} />
    <ellipse rx={r * 0.5} ry={r * 0.32} fill={BLOOD1} opacity={0.7} />
  </g>
);

const Bust: React.FC<{x: number; y: number; s?: number; lit?: number; id: string}> = ({x, y, s = 1, lit = 0, id}) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <circle cx={0} cy={-150} r={78} fill={`url(#${id}-body)`} stroke={B.rim} strokeWidth={6} />
    <path d="M -150 130 C -150 20 -80 -40 0 -40 C 80 -40 150 20 150 130 Z" fill={`url(#${id}-body)`} stroke={B.rim} strokeWidth={6} />
    <circle cx={0} cy={0} r={200} fill={B.good} opacity={0.22 * lit} />
  </g>
);

const needle = (t: number, id: string) => {
  const out = ease((t - 0.35) / 0.9); // needle slides out along its axis
  const hit = ease((t - 1.2) / 0.5);
  return (
    <>
      <g transform="translate(560 470) rotate(-26)">
        <rect x={-560} y={-300} width={1120} height={64} fill="#E9B896" />
        <rect x={-560} y={-236} width={1120} height={150} fill="#D88A78" />
        <rect x={-560} y={-86} width={1120} height={190} fill="#E9A85A" opacity={0.55} />
        {[[-380, 0, 70, 40], [-200, 30, 90, 46], [20, -10, 80, 44], [220, 36, 96, 48], [400, 0, 70, 38]].map(([x, y, rx, ry], i) => (
          <ellipse key={i} cx={x} cy={y} rx={rx} ry={ry} fill="#F2B84B" stroke="#FFD98A" strokeWidth={3} opacity={0.95} />
        ))}
        <rect x={-560} y={104} width={1120} height={260} fill="#A63A38" />
        {Array.from({length: 9}, (_, i) => <path key={i} d={`M -560 ${130 + i * 26} C -200 ${120 + i * 26} 200 ${150 + i * 26} 560 ${130 + i * 26}`} stroke="#7A1F22" strokeWidth={5} fill="none" opacity={0.7} />)}
        <rect x={-560} y={-70} width={1120} height={78} rx={39} fill="#4B4F83" />
        <rect x={-560} y={-60} width={1120} height={58} rx={29} fill="#6B2A60" />
        {Array.from({length: 16}, (_, i) => <Rbc key={i} x={-540 + ((i * 72 + t * 150) % 1120)} y={-31 + (i % 3) * 8} r={13} />)}
        {hit > 0 ? Array.from({length: 7}, (_, i) => <circle key={i} cx={-90 + i * 22 + Math.sin(t * 7 + i) * 4} cy={-70 - ((t * 120 + i * 40) % 130) * hit} r={7} fill={BLOOD0} opacity={0.9 * (1 - ((t * 120 + i * 40) % 130) / 130)} />) : null}
        <g transform={`translate(${-60 - 300 * out} ${-50 - 300 * out}) rotate(45)`}>
          <rect x={0} y={-5} width={290} height={10} rx={5} fill="#D7DEE6" />
          <rect x={-120} y={-30} width={120} height={60} rx={14} fill="rgba(255,120,120,0.55)" stroke="#FFFFFF" strokeWidth={4} />
          <rect x={-110} y={-18} width={70 * (1 - out * 0.3)} height={36} rx={8} fill={BLOOD0} />
        </g>
      </g>
      <g opacity={ease((t - 1.1) / 0.5)}>
        <path d="M 230 790 L 520 640 L 600 760 L 330 880 Z" fill="rgba(255,255,255,0.78)" />
        {Array.from({length: 9}, (_, i) => <path key={i} d={`M ${250 + i * 40} ${800 - i * 15} L ${300 + i * 40} ${860 - i * 15}`} stroke="#C9C2B4" strokeWidth={2} />)}
      </g>
      <g opacity={ease((t - 0.9) / 0.4)}>
        <circle cx={760} cy={690} r={116} fill="none" stroke="#FFFFFF" strokeWidth={5} strokeDasharray="22 14" />
        <path d="M 760 574 L 760 420" stroke="#FFFFFF" strokeWidth={4} strokeDasharray="14 10" />
        {txt(760, 400, 'ADHA LITRE', 40, '#F4EFC6')}
        <Rbc x={760} y={690} r={64} rot={-18} />
      </g>
      {txt(820, 250, `${(0.4 * ease((t - 1.0) / 2.6)).toFixed(1)} L`, 112, YEL, 'middle', 900)}
    </>
  );
};

const bag = (t: number, id: string, turn: number) => {
  const fill = ease((t - 0.3) / 2.4);
  const refill = ease((t - turn) / 3.2);
  const dropD = 'M 0 -64 C 38 -14 52 14 52 40 C 52 70 28 90 0 90 C -28 90 -52 70 -52 40 C -52 14 -38 -14 0 -64 Z';
  return (
    <>
      <g transform="translate(300 430)">
        <clipPath id={`${id}-bagc`}><path d="M -130 -200 L 130 -200 L 150 220 Q 0 260 -150 220 Z" /></clipPath>
        <path d="M -130 -200 L 130 -200 L 150 220 Q 0 260 -150 220 Z" fill="rgba(255,255,255,0.12)" stroke="#F4E8DC" strokeWidth={6} />
        <g clipPath={`url(#${id}-bagc)`}>
          <rect x={-170} y={250 - 430 * fill * 0.62} width={340} height={430} fill={BLOOD0} />
          <rect x={-170} y={250 - 430 * fill * 0.62} width={340} height={14} fill="#FF8A7A" opacity={0.7} />
        </g>
        <path d="M 0 -200 L 0 -280 C 0 -330 -120 -330 -200 -300" stroke="#D7DEE6" strokeWidth={10} fill="none" strokeLinecap="round" />
        <rect x={-60} y={-232} width={120} height={36} rx={8} fill="#EDEAE2" />
      </g>
      {Array.from({length: 10}, (_, i) => {
        const x = 640 + (i % 5) * 70, y = 330 + Math.floor(i / 5) * 190;
        const full = i === 0 ? refill : 1;
        const lost = i === 0;
        return (
          <g key={i} transform={`translate(${x} ${y}) scale(0.62)`}>
            <clipPath id={`${id}-d${i}`}><path d={dropD} /></clipPath>
            <path d={dropD} fill="rgba(20,12,12,0.55)" stroke={lost ? YEL : '#F4E8DC'} strokeWidth={lost ? 9 : 6} />
            <g clipPath={`url(#${id}-d${i})`}>
              <rect x={-60} y={96 - 170 * full} width={120} height={170} fill={lost ? BLOOD0 : '#A9232A'} opacity={lost ? 1 : 0.9} />
            </g>
          </g>
        );
      })}
      {txt(820, 250, '10%', 96, YEL, 'middle', 900)}
    </>
  );
};

const refill = (t: number, id: string) => {
  const lvl = ease((t - 0.4) / 5);
  const cells = Array.from({length: 22}, (_, i) => ({side: i % 2 ? 1 : -1, x: 0, y: 70 + Math.floor(i / 2) * 76 + (random(`cy${i}`) - 0.5) * 24}));
  return (
    <>
      <rect x={380} y={-20} width={320} height={920} fill="#4A1512" />
      <rect x={380} y={880 - 900 * (0.35 + 0.65 * lvl)} width={320} height={920} fill={BLOOD0} opacity={0.55 + 0.35 * lvl} />
      <path d="M 380 -20 L 380 900 M 700 -20 L 700 900" stroke="#F2A08C" strokeWidth={30} />
      {cells.map((c, i) => {
        const cx = 540 + c.side * (250 + random(`cx${i}`) * 120);
        return (
          <g key={i}>
            <circle cx={cx} cy={c.y} r={40} fill="#C97A78" stroke="#F0B0A8" strokeWidth={4} />
            <circle cx={cx + 6} cy={c.y - 4} r={14} fill="#7A3A40" />
          </g>
        );
      })}
      {Array.from({length: 46}, (_, i) => {
        const side = i % 2 ? 1 : -1, st = 0.5 + (i / 46) * 4.5;
        const a = ease((t - st) / 1.1);
        if (a <= 0 || a >= 1) return null;
        const sx = 540 + side * (280 + random(`wx${i}`) * 90), sy = 70 + random(`wy${i}`) * 780;
        return <circle key={i} cx={lerp(sx, 540 + (random(`wz${i}`) - 0.5) * 120, a)} cy={lerp(sy, sy + 40, a)} r={11} fill={WATER} opacity={0.95 * (1 - a * 0.5)} />;
      })}
      {Array.from({length: 4}, (_, i) => <path key={i} d={`M ${300 + (i % 2) * 40} ${200 + i * 170} h 60 m -16 -14 l 16 14 l -16 14`} stroke={WATER} strokeWidth={7} fill="none" strokeLinecap="round" opacity={0.7} />)}
      <g transform="translate(830 800)">
        <path d="M -110 0 A 110 110 0 0 1 110 0" stroke="#4A3632" strokeWidth={26} fill="none" />
        <path d="M -110 0 A 110 110 0 0 1 -35 -104" stroke={B.hurt} strokeWidth={26} fill="none" />
        <path d="M -35 -104 A 110 110 0 0 1 35 -104" stroke={YEL} strokeWidth={26} fill="none" />
        <path d="M 35 -104 A 110 110 0 0 1 110 0" stroke={B.good} strokeWidth={26} fill="none" />
        <path d={`M 0 0 L ${Math.cos(Math.PI * (1 - (0.12 + 0.76 * lvl))) * 92} ${-Math.sin(Math.PI * (1 - (0.12 + 0.76 * lvl))) * 92}`} stroke="#F4EFC6" strokeWidth={8} strokeLinecap="round" />
        <circle r={12} fill="#F4EFC6" />
        {txt(0, 48, 'PRESSURE', 32, '#F3DCC2')}
      </g>
    </>
  );
};

const plasma = (t: number, id: string) => {
  const lvl = 0.2 + 0.8 * ease((t - 0.7) / 3.6);
  const day = t < 2.4 ? 'Din 1' : 'Din 2';
  return (
    <>
      <g transform="translate(540 440)">
        <clipPath id={`${id}-tube`}><path d="M -110 -350 L 110 -350 L 110 300 Q 110 400 0 400 Q -110 400 -110 300 Z" /></clipPath>
        <path d="M -110 -350 L 110 -350 L 110 300 Q 110 400 0 400 Q -110 400 -110 300 Z" fill="rgba(255,255,255,0.1)" />
        <g clipPath={`url(#${id}-tube)`}>
          <rect x={-130} y={400 - 750 * lvl} width={260} height={760} fill={PLASMA} opacity={0.92} />
          <rect x={-130} y={400 - 750 * lvl} width={260} height={12} fill="#FFF2B8" />
          <rect x={-130} y={210} width={260} height={200} fill={BLOOD0} />
          {Array.from({length: 10}, (_, i) => <Rbc key={i} x={-80 + (i % 5) * 40} y={250 + Math.floor(i / 5) * 70} r={18} rot={i * 30} />)}
          {Array.from({length: 14}, (_, i) => <circle key={i} cx={-70 + random(`pp${i}`) * 140} cy={((t * 90 + i * 55) % 560) - 160} r={7} fill="#FFF2B8" opacity={0.8} />)}
        </g>
        <path d="M -110 -350 L 110 -350 L 110 300 Q 110 400 0 400 Q -110 400 -110 300 Z" fill="none" stroke="#F4E8DC" strokeWidth={8} />
        <rect x={-130} y={-366} width={260} height={24} rx={10} fill="#EDEAE2" />
      </g>
      <path d="M 660 300 L 760 300" stroke="#FFFFFF" strokeWidth={4} strokeDasharray="12 8" />
      {txt(790, 312, 'PLASMA', 44, '#F4EFC6', 'start')}
      {txt(250, 330, day, 84, YEL, 'middle', 900)}
    </>
  );
};

const epo = (t: number, id: string, turn: number) => {
  const sense = ease((t - 0.3) / 3.2), travel = ease((t - turn) / 3.2), make = ease((t - (turn + 3.4)) / 2);
  const bean = 'M 0 -70 C 60 -70 84 -20 70 30 C 56 84 -4 90 -40 60 C -80 24 -62 -70 0 -70 Z';
  return (
    <>
      <g transform="translate(540 180)">
        {[-1, 1].map((s) => (
          <g key={s} transform={`translate(${s * 150} 0) scale(${s} 1)`}>
            <circle r={110} fill={B.hurt} opacity={0.15 + 0.2 * sense * (0.7 + 0.3 * Math.sin(t * 7))} />
            <path d={bean} fill="#A33A34" stroke="#E8A58C" strokeWidth={6} />
            <path d="M -30 -10 C -10 0 -10 30 -30 40" stroke="#6E2A20" strokeWidth={8} fill="none" />
          </g>
        ))}
      </g>
      <g transform="translate(170 200)">
        <rect x={-18} y={-110} width={36} height={220} rx={18} fill="rgba(20,14,14,0.75)" stroke="#F4E8DC" strokeWidth={5} />
        <rect x={-9} y={110 - 200 * (1 - 0.42 * sense) + 0} width={18} height={200 * (1 - 0.42 * sense)} rx={9} fill={WATER} />
        {txt(0, -132, 'O₂', 44, WATER)}
        <path d={`M 40 -40 v ${60 * sense} m -14 -14 l 14 14 l 14 -14`} stroke={B.hurt} strokeWidth={8} fill="none" strokeLinecap="round" opacity={sense} />
      </g>
      {Array.from({length: 16}, (_, i) => {
        const q = ease((t - turn - i * 0.12) / 2.8);
        if (q <= 0 || q >= 1) return null;
        const x0 = 540 + (i % 2 ? 150 : -150), x = lerp(x0, 540, q) + Math.sin(q * 6 + i) * 24;
        return <g key={i} transform={`translate(${x} ${lerp(260, 640, q)})`} opacity={1 - q * 0.2}><circle r={13} fill={EPO} /><circle r={5} fill="#FFFFFF" opacity={0.7} /></g>;
      })}
      {travel > 0 ? txt(780, 440, 'ERYTHROPOIETIN', 34, EPO, 'start') : null}
      <g transform="translate(540 760)">
        <rect x={-300} y={-70} width={600} height={140} rx={70} fill="#E8D2B0" stroke="#FFF1D8" strokeWidth={6} />
        <rect x={-270} y={-44} width={540} height={88} rx={44} fill="#8E2A30" />
        <circle cx={-250} cy={0} r={50} fill="none" />
        <g opacity={0.4 + 0.6 * make}>
          {Array.from({length: 14}, (_, i) => <circle key={i} cx={-230 + (i % 7) * 76} cy={-18 + Math.floor(i / 7) * 36} r={22} fill="#C58BC0" stroke="#E8B0D8" strokeWidth={3} />)}
        </g>
        {Array.from({length: 12}, (_, i) => {
          const q = (((t - turn - 3.4) * 0.5 + i / 12) % 1 + 1) % 1;
          return make > 0 ? <Rbc key={i} x={-240 + (i % 6) * 96 + q * 40} y={-80 - q * 150} r={20} rot={q * 200} o={Math.sin(q * Math.PI)} /> : null;
        })}
      </g>
      {make > 0 ? txt(540, 640 - 30, 'TEZ BANAO!', 56, YEL, 'middle', 900) : null}
    </>
  );
};

const weeks = (t: number) => {
  const rc = ease((t - 0.5) / 3.2), fe = 0.7 * ease((t - 0.5) / 5.2);
  const bar = (y: number, label: string, tag: string, p: number, col: string, ticks: string[]) => (
    <g>
      {txt(150, y - 48, label, 46, '#F4EFC6', 'start')}
      <rect x={150} y={y} width={780} height={64} rx={32} fill="rgba(20,14,14,0.75)" stroke="#F4E8DC" strokeWidth={5} />
      <rect x={156} y={y + 6} width={Math.max(0, 768 * p)} height={52} rx={26} fill={col} />
      {ticks.map((k, i) => <text key={i} x={150 + (780 * (i + 1)) / ticks.length - 40} y={y + 104} fontFamily={FONT} fontWeight={700} fontSize={32} fill="#F3DCC2" textAnchor="middle">{k}</text>)}
      {txt(930, y - 48, tag, 40, YEL, 'end', 900)}
    </g>
  );
  return (
    <>
      {bar(220, 'RED CELLS', '4–8 HAFTE', rc, BLOOD0, ['1', '2', '3', '4', '5', '6', '7', '8'])}
      {bar(560, 'IRON', 'KAI MAHINE', fe, '#E09A4A', ['M1', 'M2', 'M3', 'M4'])}
      {Array.from({length: 8}, (_, i) => <Rbc key={i} x={200 + ((i * 95 + t * 60) % 700)} y={430 + Math.sin(t * 3 + i) * 10} r={22} rot={i * 25} o={0.9 * rc} />)}
    </>
  );
};

const three = (t: number, id: string, turn: number) => {
  const split = ease((t - turn) / 1.4);
  const parts = [{x: 230, c: BLOOD0, n: 'RED CELLS'}, {x: 540, c: PLASMA, n: 'PLASMA'}, {x: 850, c: '#F0E6D0', n: 'PLATELETS'}];
  const lives = Math.round(3 * ease((t - turn - 1.4) / 1.6));
  return (
    <>
      <g transform={`translate(540 ${lerp(300, 180, split)}) scale(${lerp(1, 0.55, split)})`} opacity={1 - split * 0.5}>
        <path d="M -110 -110 L 110 -110 L 124 130 Q 0 160 -124 130 Z" fill="rgba(255,255,255,0.14)" stroke="#F4E8DC" strokeWidth={7} />
        <path d="M -118 20 L 118 20 L 124 130 Q 0 160 -124 130 Z" fill={BLOOD0} />
      </g>
      {parts.map((p, i) => (
        <g key={i} transform={`translate(${lerp(540, p.x, split)} ${lerp(200, 400, split)})`} opacity={split}>
          <path d="M -50 -60 L 50 -60 L 56 70 Q 0 90 -56 70 Z" fill="rgba(255,255,255,0.14)" stroke="#F4E8DC" strokeWidth={6} />
          <path d="M -54 -10 L 54 -10 L 56 70 Q 0 90 -56 70 Z" fill={p.c} />
          {txt(0, 140, p.n, 30, '#F4EFC6')}
        </g>
      ))}
      {parts.map((p, i) => {
        const lit = ease((t - turn - 1.4 - i * 0.5) / 0.6);
        return (
          <g key={i}>
            <path d={`M ${p.x} 560 v ${60 * split}`} stroke={p.c} strokeWidth={8} strokeDasharray="4 14" opacity={split} />
            <Bust x={p.x} y={780} s={0.62} lit={lit} id={id} />
            <g opacity={lit}><circle cx={p.x + 70} cy={640} r={26} fill={B.good} />{txt(p.x + 70, 652, '✓', 36, '#0E1F10')}</g>
          </g>
        );
      })}
      {txt(540, 40, `${lives} JAAN`, 76, YEL, 'middle', 900)}
    </>
  );
};

const friend = (t: number, id: string) => {
  const pop = ease((t - 0.3) / 0.5), beat = 1 + 0.08 * Math.max(0, Math.sin(t * 7)) ** 4;
  const dropD = 'M 0 -64 C 38 -14 52 14 52 40 C 52 70 28 90 0 90 C -28 90 -52 70 -52 40 C -52 14 -38 -14 0 -64 Z';
  return (
    <>
      <g transform={`translate(540 250) scale(${2.1 * beat * pop})`} filter={`url(#${id}-shadow)`}>
        <path d={dropD} fill={BLOOD0} stroke="#FF8A7A" strokeWidth={4} />
        <path d="M 0 62 C -34 38 -26 12 -10 14 C -2 16 0 24 0 24 C 0 24 2 16 10 14 C 26 12 34 38 0 62 Z" fill="#FFE0DA" />
      </g>
      <Bust x={270} y={760} s={1} id={id} />
      <Bust x={810} y={760} s={1} lit={ease((t - 1.4) / 0.6)} id={id} />
      <g transform="translate(540 590)" opacity={ease((t - 0.9) / 0.4)}>
        <rect x={-150} y={-60} width={300} height={110} rx={50} fill="#F4EFC6" />
        <path d="M -40 50 L -70 90 L 0 50 Z" fill="#F4EFC6" />
        {[-60, 0, 60].map((x, i) => <circle key={i} cx={x} cy={-5 + Math.sin(t * 8 + i) * 8} r={13} fill="#3A2A22" />)}
      </g>
      <path d="M 340 520 C 440 400 640 400 740 520 m -18 -26 l 18 26 l -34 4" stroke={YEL} strokeWidth={10} fill="none" strokeLinecap="round" opacity={ease((t - 1.1) / 0.5)} />
    </>
  );
};

export const donateArt = (p: BodyProps, id: string, t: number): React.ReactNode => {
  const turn = p.turn_at_s ?? 3;
  switch (p.shot) {
    case 'needle': return needle(t, id);
    case 'bag': return bag(t, id, turn);
    case 'refill': return refill(t, id);
    case 'plasma': return plasma(t, id);
    case 'epo': return epo(t, id, turn);
    case 'weeks': return weeks(t);
    case 'three': return three(t, id, turn);
    case 'friend': return friend(t, id);
    default: return undefined;
  }
};
