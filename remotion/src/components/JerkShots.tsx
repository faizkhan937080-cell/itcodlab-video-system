// Hypnic jerk (neend ka jhatka) explainer shots. Same realistic SVG look as Spicy/Cold. Deterministic. Art area x 120..960, y 0..880.
import React from 'react';
import {random} from 'remotion';
import {FONT, ramp, lerp} from './MedScene';
import type {BodyProps} from './BodyScene';

const NAVY = '#0F1B3D', MOON = '#FFF3B0', YEL = '#FFE066', RED = '#E5332A', GOOD = '#7BE38B', SKIN = '#E8A98A', BLUE = '#8FB8FF';
const ease = (q: number) => 1 - (1 - Math.min(1, Math.max(0, q))) ** 3;
const txt = (x: number, y: number, s: string, size: number, fill = '#EAF0FF', anchor: 'start' | 'middle' | 'end' = 'middle', w = 800) => (
  <text x={x} y={y} textAnchor={anchor} fontFamily={FONT} fontWeight={w} fontSize={size} fill={fill} stroke="#070D22" strokeWidth={size * 0.16} style={{paintOrder: 'stroke'}}>{s}</text>
);
const Stars: React.FC<{t: number}> = ({t}) => (
  <>
    {Array.from({length: 30}, (_, i) => <circle key={i} cx={120 + random(`st${i}x`) * 840} cy={random(`st${i}y`) * 560} r={2 + random(`st${i}r`) * 3} fill="#FFFFFF" opacity={0.3 + 0.5 * Math.abs(Math.sin(t * 1.4 + i))} />)}
  </>
);
const Moon: React.FC<{x: number; y: number}> = ({x, y}) => (
  <g><circle cx={x} cy={y} r={70} fill={MOON} /><circle cx={x + 28} cy={y - 14} r={62} fill={NAVY} /></g>
);
/** Sleeper lying in bed, seen from side. jerk 0..1 = body lifts and arm flings. */
const Sleeper: React.FC<{x: number; y: number; jerk: number; id: string}> = ({x, y, jerk, id}) => (
  <g transform={`translate(${x} ${y - jerk * 70}) rotate(${-jerk * 9})`}>
    <g filter={`url(#${id}-shadow)`}>
      <rect x={-250} y={0} width={500} height={90} rx={40} fill="#4B6FD6" />
      <circle cx={-200} cy={-20} r={62} fill={SKIN} />
      <path d="M -250 -60 C -220 -110 -150 -100 -130 -60 Z" fill="#2A1A14" />
      <path d={`M -120 10 L ${40 + jerk * 40} ${-30 - jerk * 90}`} stroke={SKIN} strokeWidth={34} strokeLinecap="round" />
      <ellipse cx={-215} cy={-26} rx={7} ry={jerk > 0.3 ? 12 : 3} fill="#1A1A1A" />
    </g>
  </g>
);
const Bed: React.FC = () => (
  <g><rect x={150} y={640} width={800} height={50} rx={14} fill="#5B3A29" /><rect x={150} y={690} width={36} height={110} fill="#3E271B" /><rect x={914} y={690} width={36} height={110} fill="#3E271B" /></g>
);

const hook = (p: BodyProps, id: string, t: number) => {
  const j = ease((t - 2.4) / 0.25) * (1 - ease((t - 3.0) / 0.5));
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} />
      <Stars t={t} /><Moon x={820} y={170} />
      <Bed /><Sleeper x={520} y={560} jerk={j} id={id} />
      {j > 0.2 && <g>{[-1, 1].map((s) => <path key={s} d={`M ${520 + s * 260} 330 l ${s * 60} -40 M ${520 + s * 280} 400 l ${s * 70} 0`} stroke={YEL} strokeWidth={10} strokeLinecap="round" />)}</g>}
      {txt(540, 120, 'NEEND MEIN JHATKA?!', 58, YEL, 'middle', 900)}
      {j > 0.2 && txt(540, 470, 'AAH!', 110, RED, 'middle', 900)}
    </>
  );
};

const stat = (p: BodyProps, id: string, t: number) => {
  const n = Math.min(10, Math.floor(t / 0.3));
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} opacity={0.6} />
      {Array.from({length: 10}, (_, i) => {
        const cx = 230 + (i % 5) * 150, cy = 330 + Math.floor(i / 5) * 230, on = i < Math.min(7, n), show = i < n;
        return show ? (
          <g key={i} transform={`translate(${cx} ${cy})`} opacity={0.95}>
            <circle cy={-50} r={36} fill={on ? YEL : '#6C7AA8'} />
            <path d="M -48 70 C -48 0 48 0 48 70 Z" fill={on ? YEL : '#6C7AA8'} />
          </g>
        ) : null;
      })}
      {txt(540, 130, 'HYPNIC JERK', 72, YEL, 'middle', 900)}
      {txt(540, 790, `${Math.min(7, n)} / 10 LOG`, 84, n >= 7 ? GOOD : '#EAF0FF', 'middle', 900)}
    </>
  );
};

const brain = (p: BodyProps, id: string, t: number) => {
  const relax = ease((t - 0.5) / 2.0), alarm = ease((t - 2.6) / 0.4);
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} opacity={0.5} />
      <g transform="translate(540 330)" filter={`url(#${id}-shadow)`}>
        <g filter={`url(#${id}-flesh)`}><path d="M -200 20 C -230 -150 -80 -230 0 -190 C 80 -230 230 -150 200 20 C 220 130 90 190 0 160 C -90 190 -220 130 -200 20 Z" fill="#E9929C" /></g>
        <path d="M 0 -190 C 20 -100 -20 -40 0 160" stroke="#B85A6A" strokeWidth={8} fill="none" />
        {alarm > 0.1 && <g opacity={alarm}><circle r={250} fill="none" stroke={RED} strokeWidth={12} strokeDasharray="30 22" /><path d="M -30 -20 L 20 -90 L 10 -20 L 40 -20 L -20 70 L -10 -10 Z" fill={YEL} /></g>}
      </g>
      <g transform="translate(540 700)">
        <rect x={-260} y={-30} width={520} height={70} rx={35} fill="#4B6FD6" />
        <rect x={-260} y={-30} width={lerp(520, 130, relax)} height={70} rx={35} fill="#3556B6" />
        <path d={`M ${-250} 0 q ${lerp(0, 30, relax)} ${lerp(-30, 30, relax)} 60 0`} stroke="#9DB9FF" strokeWidth={6} fill="none" />
      </g>
      {txt(540, 110, 'MUSCLE DHEELE', 52, BLUE, 'middle', 900)}
      {txt(540, 840, alarm > 0.5 ? '“ARRE GIR RAHA HOON!”' : 'DIMAAG: ??', 46, alarm > 0.5 ? RED : '#EAF0FF', 'middle', 900)}
    </>
  );
};

const monkey = (p: BodyProps, id: string, t: number) => {
  const fall = ease((t - 2.2) / 0.5) * (1 - ease((t - 3.2) / 0.6)), sway = Math.sin(t * 2) * 6;
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill="#10331F" opacity={0.75} />
      <Moon x={800} y={190} />
      <g filter={`url(#${id}-shadow)`}>
        <rect x={340} y={300} width={120} height={600} fill="#5B3A29" />
        <path d="M 400 420 L 800 330 L 810 380 L 400 480 Z" fill="#5B3A29" />
        <circle cx={300} cy={260} r={150} fill="#2F7A3F" /><circle cx={520} cy={230} r={140} fill="#3B9150" />
      </g>
      <g transform={`translate(${620} ${300 + fall * 260 + sway * 0.3}) rotate(${fall * -25})`} filter={`url(#${id}-shadow)`}>
        <ellipse cx={0} cy={20} rx={70} ry={55} fill="#8A5A3A" />
        <circle cx={0} cy={-55} r={46} fill="#8A5A3A" /><circle cx={0} cy={-45} r={30} fill="#E5B58F" />
        <circle cx={-12} cy={-52} r={5} fill="#111" /><circle cx={12} cy={-52} r={5} fill="#111" />
        <path d={`M 60 40 C 130 60 150 ${lerp(-20, 30, fall)} 110 -20`} stroke="#8A5A3A" strokeWidth={18} fill="none" strokeLinecap="round" />
      </g>
      {fall > 0.3 && txt(620, 220, 'AAAH!', 80, RED, 'middle', 900)}
      {txt(540, 110, 'PURANI ADAT', 54, YEL, 'middle', 900)}
      {txt(540, 840, 'PED PE SONA = GIRNA KHATARNAK', 36, '#EAF0FF', 'middle', 800)}
    </>
  );
};

const half = (p: BodyProps, id: string, t: number) => {
  const a = ease(t / 0.5), blink = t > 0.6 ? 1 : 0;
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} opacity={0.5} />
      <g transform="translate(540 430)" filter={`url(#${id}-shadow)`}>
        <circle r={250} fill="#0B1330" stroke="#EAF0FF" strokeWidth={10} />
        <path d={`M 0 0 L 0 -250 A 250 250 0 0 1 ${Math.sin(Math.PI * a) * 250} ${-Math.cos(Math.PI * a) * 250} Z`} fill={RED} opacity={0.85} />
        <circle r={26} fill="#EAF0FF" />
      </g>
      {txt(540, 130, 'SIRF', 54, BLUE, 'middle', 900)}
      {txt(540, 810, blink ? '0.5 SECOND!' : '…', 100, YEL, 'middle', 900)}
    </>
  );
};

const Cup: React.FC<{x: number; y: number; t: number}> = ({x, y, t}) => (
  <g transform={`translate(${x} ${y})`}>
    <path d="M -70 -60 L 70 -60 L 55 70 Q 0 95 -55 70 Z" fill="#E8E2D2" /><path d="M -60 -50 L 60 -50 L 50 0 L -50 0 Z" fill="#7A4A2A" />
    <path d="M 70 -30 q 55 0 40 45 q -10 25 -45 20" stroke="#E8E2D2" strokeWidth={14} fill="none" />
    {[-25, 5, 35].map((o, i) => <path key={i} d={`M ${o} -80 q 14 -30 0 -55 q -14 -25 0 -50`} stroke="#EAF0FF" strokeWidth={7} fill="none" opacity={0.5 + 0.4 * Math.sin(t * 3 + i)} transform={`translate(0 ${-((t * 30 + i * 12) % 30)})`} />)}
  </g>
);
const triggers = (p: BodyProps, id: string, t: number) => {
  const items = [0.4, 1.4, 2.6, 3.8];
  const lab = ['CHAI/COFFEE', 'TENSION', 'KAM NEEND', 'NIGHT WORKOUT'];
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} opacity={0.55} />
      {items.map((st, i) => {
        const q = ease((t - st) / 0.4), cx = 330 + (i % 2) * 420, cy = 300 + Math.floor(i / 2) * 330;
        return (
          <g key={i} opacity={q} transform={`translate(0 ${(1 - q) * 40})`} filter={`url(#${id}-shadow)`}>
            <rect x={cx - 180} y={cy - 130} width={360} height={280} rx={40} fill="rgba(234,240,255,0.12)" stroke="#EAF0FF" strokeWidth={5} />
            {i === 0 && <Cup x={cx} y={cy - 20} t={t} />}
            {i === 1 && <g transform={`translate(${cx} ${cy - 20})`}><circle r={70} fill={YEL} /><path d="M -35 -20 q 12 -12 24 0 M 11 -20 q 12 -12 24 0" stroke="#111" strokeWidth={8} fill="none" /><path d="M -35 35 q 35 -30 70 0" stroke="#111" strokeWidth={8} fill="none" /></g>}
            {i === 2 && <g transform={`translate(${cx} ${cy - 20})`}><circle r={70} fill="#9FB4E8" /><path d="M -40 -10 h 28 M 12 -10 h 28" stroke="#111" strokeWidth={8} /><text y={-70} x={70} fontFamily={FONT} fontWeight={900} fontSize={50} fill={BLUE}>Zzz</text></g>}
            {i === 3 && <g transform={`translate(${cx} ${cy - 20})`}><rect x={-90} y={-14} width={180} height={28} rx={12} fill="#CFCFCF" /><rect x={-120} y={-44} width={36} height={88} rx={10} fill="#8A8A8A" /><rect x={84} y={-44} width={36} height={88} rx={10} fill="#8A8A8A" /></g>}
            {txt(cx, cy + 120, lab[i], 30, YEL, 'middle', 900)}
          </g>
        );
      })}
      {txt(540, 110, 'JHATKA BADHATE HAIN', 48, RED, 'middle', 900)}
    </>
  );
};

const fix = (p: BodyProps, id: string, t: number) => {
  const phoneX = lerp(380, 880, ease((t - 0.5) / 1.2)), dark = ease((t - 2.2) / 1.2);
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} />
      <rect x={100} y={0} width={880} height={900} fill="#000" opacity={dark * 0.45} />
      <Stars t={t} /><Moon x={800} y={160} />
      <Bed /><g opacity={1}><rect x={250} y={540} width={380} height={100} rx={40} fill="#4B6FD6" /><circle cx={270} cy={520} r={54} fill={SKIN} /></g>
      <g transform={`translate(${phoneX} 560)`} filter={`url(#${id}-shadow)`}>
        <rect x={-48} y={-90} width={96} height={180} rx={18} fill="#222" stroke="#EAF0FF" strokeWidth={5} /><rect x={-38} y={-78} width={76} height={150} rx={8} fill={BLUE} />
      </g>
      {txt(540, 110, 'SONE SE PEHLE', 52, BLUE, 'middle', 900)}
      {txt(540, 790, t < 1.8 ? 'PHONE DOOR' : t < 3.4 ? 'CHAI BAND' : 'ANDHERA + SHAANT', 62, GOOD, 'middle', 900)}
    </>
  );
};

const endj = (p: BodyProps, id: string, t: number) => {
  const comments = ['Kal raat hua tha!', 'Ye toh roz hota hai', 'Bandar wali baat sahi', 'Chai band karta hoon'];
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill={NAVY} opacity={0.5} />
      <Stars t={t} />
      <g transform="translate(250 560) scale(0.8)"><Bed /></g>
      {comments.map((c, i) => {
        const st = 0.5 + i * 0.7, q = ease((t - st) / 0.5), y = lerp(880, 120 + i * 190, q);
        return (
          <g key={i} opacity={q}>
            <rect x={lerp(540, 440, q)} y={y} width={500} height={110} rx={55} fill="#EAF0FF" />
            <circle cx={lerp(540, 440, q) + 55} cy={y + 55} r={34} fill={['#E5332A', '#FF8A1F', '#7BE38B', '#8FB8FF'][i]} />
            {txt(lerp(540, 440, q) + 105, y + 68, c, 32, '#0B1420', 'start', 800)}
          </g>
        );
      })}
    </>
  );
};

export const jerkArt = (p: BodyProps, id: string, t: number): React.ReactNode => {
  switch (p.shot) {
    case 'je_hook': return hook(p, id, t);
    case 'je_stat': return stat(p, id, t);
    case 'je_brain': return brain(p, id, t);
    case 'je_monkey': return monkey(p, id, t);
    case 'je_half': return half(p, id, t);
    case 'je_triggers': return triggers(p, id, t);
    case 'je_fix': return fix(p, id, t);
    case 'je_end': return endj(p, id, t);
    default: return undefined;
  }
};
