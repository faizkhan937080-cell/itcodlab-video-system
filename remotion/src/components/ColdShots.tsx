// Cold-weather bladder explainer shots (cold diuresis), same realistic SVG look as SpicyShots. Deterministic (seeded).
// Art area (after the 1.12 zoom in BodyScene) is design x 120..960, y 0..880.
import React from 'react';
import {random} from 'remotion';
import {FONT, ramp, lerp} from './MedScene';
import type {BodyProps} from './BodyScene';

const ICE = '#8FD3FF', YEL = '#FFE066', RED = '#E5332A', PEE = '#F3D45A', GOOD = '#7BE38B';
const ease = (q: number) => 1 - (1 - Math.min(1, Math.max(0, q))) ** 3;
const txt = (x: number, y: number, s: string, size: number, fill = '#E8F4FF', anchor: 'start' | 'middle' | 'end' = 'middle', w = 800) => (
  <text x={x} y={y} textAnchor={anchor} fontFamily={FONT} fontWeight={w} fontSize={size} fill={fill} stroke="#0B1420" strokeWidth={size * 0.16} style={{paintOrder: 'stroke'}}>{s}</text>
);

const Snow: React.FC<{t: number; n?: number}> = ({t, n = 36}) => (
  <>
    {Array.from({length: n}, (_, i) => {
      const x = 120 + random(`sn${i}x`) * 840, sp = 60 + random(`sn${i}s`) * 90, r = 3 + random(`sn${i}r`) * 6;
      const y = ((t * sp + random(`sn${i}y`) * 900) % 940) - 30;
      return <circle key={i} cx={x + Math.sin(t * 1.5 + i) * 14} cy={y} r={r} fill="#FFFFFF" opacity={0.35 + random(`sn${i}o`) * 0.5} />;
    })}
  </>
);

/** Bladder: round dome, two ureters on top, narrow urethra below. origin = centre. level 0..1 = pale-yellow fill. */
const BL = 'M -170 -40 C -170 -190 170 -190 170 -40 C 170 60 80 120 40 170 L 40 240 L -40 240 L -40 170 C -80 120 -170 60 -170 -40 Z';
const Bladder: React.FC<{id: string; x: number; y: number; s?: number; level?: number; t: number; scarf?: boolean; shiver?: number}> = ({id, x, y, s = 1, level = 0.3, t, scarf = false, shiver = 0}) => {
  const jx = Math.sin(t * 70) * 5 * shiver, jy = Math.cos(t * 63) * 4 * shiver;
  const top = lerp(240, -170, level);
  return (
    <g transform={`translate(${x + jx} ${y + jy}) scale(${s})`} filter={`url(#${id}-shadow)`}>
      <clipPath id={`${id}-bl`}><path d={BL} /></clipPath>
      <path d="M -110 -120 C -120 -200 -150 -240 -170 -290 M 110 -120 C 120 -200 150 -240 170 -290" stroke="#D77A74" strokeWidth={26} fill="none" strokeLinecap="round" />
      <g filter={`url(#${id}-flesh)`}><path d={BL} fill="#E98A86" /></g>
      <g clipPath={`url(#${id}-bl)`}>
        <rect x={-260} y={top} width={520} height={400} fill={PEE} opacity={0.88} />
        <path d={`M -260 ${top} q 65 -${10 + Math.sin(t * 4) * 4} 130 0 t 130 0 t 130 0 t 130 0`} stroke="#FFF3B0" strokeWidth={6} fill="none" />
      </g>
      <path d="M -140 -80 C -110 -150 -40 -170 20 -168" stroke="#FFFFFF" strokeWidth={9} fill="none" strokeLinecap="round" opacity={0.5} />
      {scarf && (
        <g>
          <path d="M -70 150 C -20 176 20 176 70 150 L 78 196 C 20 222 -20 222 -78 196 Z" fill="#E5332A" stroke="#FFB0A6" strokeWidth={4} />
          <path d="M 40 190 L 80 290 L 30 296 L 12 196 Z" fill="#C42A22" stroke="#FFB0A6" strokeWidth={4} />
        </g>
      )}
    </g>
  );
};

const hook = (p: BodyProps, id: string, t: number) => {
  const drop = ease(t / 1.6), temp = Math.round(lerp(22, 8, drop));
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill="#16324F" opacity={0.35} />
      <Snow t={t} />
      <Bladder id={id} x={620} y={470} s={0.95} level={0.2 + 0.5 * ease((t - 1.0) / 2.5)} t={t} scarf shiver={ramp(t, 0.6, 1.2)} />
      <g transform="translate(250 0)">
        <rect x={-30} y={90} width={60} height={620} rx={30} fill="rgba(255,255,255,0.12)" stroke="#E8F2FF" strokeWidth={5} />
        <circle cx={0} cy={740} r={58} fill="rgba(255,255,255,0.12)" stroke="#E8F2FF" strokeWidth={5} />
        <circle cx={0} cy={740} r={42} fill={ICE} />
        <rect x={-12} y={lerp(180, 520, drop)} width={24} height={740 - lerp(180, 520, drop)} fill={ICE} />
      </g>
      {txt(250, 62, `${temp}°C`, 84, ICE, 'middle', 900)}
      {txt(620, 150, 'THAND = TOILET?!', 56, YEL, 'middle', 900)}
    </>
  );
};

const vessels = (p: BodyProps, id: string, t: number) => {
  const squeeze = ease((t - 0.8) / 2.2);
  const w = lerp(70, 8, squeeze);
  const ys = [220, 400, 580];
  return (
    <>
      <rect x={100} y={0} width={880} height={900} fill="#16324F" opacity={0.3} />
      {txt(290, 100, 'HAATH-PAIR', 34, ICE, 'middle', 900)}
      {txt(780, 100, 'CORE', 34, '#FF9C8E', 'middle', 900)}
      {ys.map((y, k) => (
        <g key={k}>
          <rect x={130} y={y - w / 2} width={520} height={w} rx={w / 2} fill="#B83A3A" stroke="#FFB0A6" strokeWidth={3} filter={`url(#${id}-gloss)`} />
          {Array.from({length: 7}, (_, i) => {
            const q = (((t * 0.55 + i / 7 + k * 0.17) % 1) + 1) % 1;
            return <circle key={i} cx={lerp(150, 640, q)} cy={y} r={Math.min(15, w / 2 - 2)} fill="#FFD0C8" opacity={0.85} />;
          })}
        </g>
      ))}
      <g filter={`url(#${id}-flesh)`}>
        <ellipse cx={800} cy={400} rx={150} ry={300} fill="#8E1E1C" />
      </g>
      {Array.from({length: 14}, (_, i) => {
        const q = ((t * 0.7 + i / 14) % 1);
        return <circle key={i} cx={lerp(650, 780, q)} cy={lerp(ys[i % 3], 400 + Math.sin(i) * 90, q)} r={9} fill="#FFD0C8" opacity={0.5 + 0.5 * squeeze} />;
      })}
      {txt(540, 800, squeeze > 0.8 ? 'NASEIN SIKUD GAYI → KHOON ANDAR' : 'THAND: GARMI BACHAO MODE', 34, squeeze > 0.8 ? YEL : '#E8F4FF', 'middle', 800)}
    </>
  );
};

const pressure = (p: BodyProps, id: string, t: number) => {
  const up = ease((t - 0.6) / 2.4), val = Math.round(lerp(120, 150, up));
  const ang = lerp(-60, 55, up);
  return (
    <>
      <g transform="translate(540 500) scale(0.86)" filter={`url(#${id}-shadow)`}>
        <circle r={290} fill="#0E1B2A" stroke="#E8F2FF" strokeWidth={8} />
        <path d="M -250 0 A 250 250 0 0 1 250 0" stroke={GOOD} strokeWidth={26} fill="none" opacity={0.8} />
        <path d="M 120 -219 A 250 250 0 0 1 250 0" stroke={RED} strokeWidth={26} fill="none" opacity={0.9} />
        <g transform={`rotate(${ang})`}><path d="M -10 20 L 0 -230 L 10 20 Z" fill={YEL} /><circle r={26} fill="#E8F2FF" /></g>
      </g>
      {txt(540, 850, `PRESSURE ${val}`, 84, up > 0.8 ? RED : YEL, 'middle', 900)}
      {txt(540, 90, 'ANDAR KHOON ZYADA', 42, '#FF9C8E', 'middle', 900)}
      {txt(540, 148, 'JAGAH KAM!', 42, YEL, 'middle', 900)}
    </>
  );
};

const kidney = (p: BodyProps, id: string, t: number) => {
  const off = ease((t - 1.2) / 0.6);
  return (
    <>
      <g filter={`url(#${id}-flesh)`}>
        <path d="M 440 150 C 240 120 150 330 250 520 C 330 670 470 690 560 620 C 470 560 520 470 600 440 C 520 380 580 300 640 270 C 600 190 520 160 440 150 Z" fill="#B5563E" transform="translate(90 20)" />
      </g>
      {Array.from({length: 16}, (_, i) => {
        const q = (((t * 0.6 + i / 16) % 1) + 1) % 1;
        return <circle key={i} cx={lerp(450, 520, q) + Math.sin(i) * 40} cy={lerp(330, 820, q)} r={11} fill="#9EDCFF" opacity={Math.sin(q * Math.PI) * (0.4 + 0.6 * off)} />;
      })}
      <g transform="translate(780 330)">
        <rect x={-120} y={-70} width={240} height={140} rx={30} fill={off > 0.5 ? '#2B2B2F' : '#2E7D32'} stroke="#FFFFFF" strokeWidth={5} />
        {txt(0, -6, 'ADH', 52, '#FFFFFF', 'middle', 900)}
        {txt(0, 44, off > 0.5 ? 'BAND (OFF)' : 'ON', 34, off > 0.5 ? '#FF9C8E' : GOOD, 'middle', 800)}
      </g>
      {txt(540, 100, 'KIDNEY', 48, '#FFD0B8', 'middle', 900)}
      {txt(540, 850, off > 0.5 ? 'PAANI ROKNA BAND → CHHANNA SHURU' : 'ADH = PAANI ROKNE WALA HORMONE', 34, off > 0.5 ? YEL : '#E8F4FF', 'middle', 800)}
    </>
  );
};

const bladder = (p: BodyProps, id: string, t: number) => {
  const l0 = (p.count_to ?? 12) / 100, lvl = l0 + (0.95 - l0) * ease((t - 0.4) / 3.6);
  return (
    <>
      <Bladder id={id} x={540} y={470} s={1.0} level={lvl} t={t} scarf shiver={ramp(t, 2.6, 3.4)} />
      {txt(540, 150, 'BLADDER: HOUSEFULL', 54, YEL, 'middle', 900)}
      {txt(540, 850, `${Math.round(lvl * 100)}% BHARA`, 64, lvl > 0.8 ? RED : '#E8F4FF', 'middle', 900)}
    </>
  );
};

const water = (p: BodyProps, id: string, t: number) => {
  const fill = ease((t - 0.5) / 2.0);
  return (
    <>
      <g transform="translate(540 430)" filter={`url(#${id}-shadow)`}>
        <path d="M -140 -240 L 140 -240 L 110 250 Q 0 280 -110 250 Z" fill={`url(#${id}-glass)`} stroke="#E8F6FF" strokeWidth={6} />
        <path d={`M -${lerp(10, 128, fill)} ${lerp(240, -130, fill)} L ${lerp(10, 128, fill)} ${lerp(240, -130, fill)} L 106 246 Q 0 274 -106 246 Z`} fill="#7CCBFF" opacity={0.7} />
      </g>
      {fill > 0.9 && <g transform="translate(790 300)"><circle r={74} fill={GOOD} /><path d="M -34 2 L -8 30 L 38 -26" stroke="#0B1420" strokeWidth={16} fill="none" strokeLinecap="round" strokeLinejoin="round" /></g>}
      {txt(540, 110, 'PAANI MAT CHHODO', 60, '#9EDCFF', 'middle', 900)}
      {txt(540, 830, 'THAND MEIN BHI PAANI CHAHIYE', 38, YEL, 'middle', 800)}
    </>
  );
};

const endc = (p: BodyProps, id: string, t: number) => {
  const comments = ['Har ghante?!', 'Ye toh main hoon', 'Sweater pehno bhai', 'Bladder ka scene'];
  return (
    <>
      <Snow t={t} n={20} />
      <Bladder id={id} x={230} y={470} s={0.7} level={0.55} t={t} scarf shiver={0.6} />
      {comments.map((c, i) => {
        const st = 0.5 + i * 0.7, q = ease((t - st) / 0.5);
        const y = lerp(880, 120 + i * 190, q);
        return (
          <g key={i} opacity={q}>
            <rect x={lerp(540, 440, q)} y={y} width={480} height={110} rx={55} fill="#E8F4FF" />
            <circle cx={lerp(540, 440, q) + 55} cy={y + 55} r={34} fill={['#E5332A', '#FF8A1F', '#7BE38B', '#8FD3FF'][i]} />
            {txt(lerp(540, 440, q) + 105, y + 68, c, 34, '#0B1420', 'start', 800)}
          </g>
        );
      })}
    </>
  );
};

export const coldArt = (p: BodyProps, id: string, t: number): React.ReactNode => {
  switch (p.shot) {
    case 'co_hook': return hook(p, id, t);
    case 'co_vessels': return vessels(p, id, t);
    case 'co_pressure': return pressure(p, id, t);
    case 'co_kidney': return kidney(p, id, t);
    case 'co_bladder': return bladder(p, id, t);
    case 'co_water': return water(p, id, t);
    case 'co_end': return endc(p, id, t);
    default: return undefined;
  }
};
