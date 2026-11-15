// Body explainer shots (tea + cigarette), drawn in SVG in the same warm anatomy look as MedScene:
// x-ray torso with glowing organs, chai glass with steam, cigarette with ember and smoke, macro food-pipe wall.
// Deterministic (seeded). Design space 1080 x 1920. Shared look pieces come from MedScene; shots B live in BodyShots.tsx.
import React from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {unit} from '../lib/anim';
import {C, Defs, Backdrop, Headline, Pill, FONT, ramp, sec, along, lerp} from './MedScene';
import type {Seg} from './MedScene';
import {shotArt} from './BodyShots';

export type BodyProps = {
  shot: 'hook' | 'scald' | 'smoke_settle' | 'study' | 'heart' | 'liver' | 'cool' | 'end';
  headline?: string;
  headline_at_s?: number;
  headline2?: string; // replaces the headline at turn_at_s
  turn_at_s?: number; // hook: objects go inside the body; cool: cigarette drops
  sub?: string;
  sub_at_s?: number;
  chips?: {text: string; at_s: number}[];
  big?: string;
  big_at_s?: number;
  count_to?: number; // study: yellow count-up number
  count_suffix?: string;
  labels?: string[]; // study: two bar labels; cool: thermometer label
  locale?: string;
  badge?: string;
  badge_at_s?: number;
};

export const B = {
  tea0: '#E2A04A', tea1: '#9A5318', teaHot: '#FFB23E', glass: 'rgba(255,255,255,0.5)',
  paper0: '#FBF7EE', paper1: '#CFC8BA', filter0: '#E09A4A', filter1: '#B36A22', ember: '#FF5A1F',
  smoke: '#E4DED6', skin: '#2A1C1B', rim: '#F2B48C', pipe0: '#F2A08C', pipe1: '#B85848', pipeIn: '#7A2A26',
  hurt: '#E5332A', lung: '#D98A7A', heart0: '#E5483C', heart1: '#8E1E1C', liver0: '#B5563E', liver1: '#6E2A20',
  good: '#7BE38B', cold: '#8FD3FF',
};

export const BodyDefs: React.FC<{id: string}> = ({id}) => (
  <defs>
    <linearGradient id={`${id}-tea`} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={B.tea0} />
      <stop offset="100%" stopColor={B.tea1} />
    </linearGradient>
    <linearGradient id={`${id}-paper`} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={B.paper0} />
      <stop offset="100%" stopColor={B.paper1} />
    </linearGradient>
    <linearGradient id={`${id}-filt`} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor={B.filter0} />
      <stop offset="100%" stopColor={B.filter1} />
    </linearGradient>
    <radialGradient id={`${id}-ember`}>
      <stop offset="0%" stopColor="#FFF1B8" stopOpacity="1" />
      <stop offset="35%" stopColor={B.ember} stopOpacity="0.95" />
      <stop offset="100%" stopColor={B.ember} stopOpacity="0" />
    </radialGradient>
    <linearGradient id={`${id}-pipe`} x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stopColor={B.pipe1} />
      <stop offset="50%" stopColor={B.pipe0} />
      <stop offset="100%" stopColor={B.pipe1} />
    </linearGradient>
    <radialGradient id={`${id}-heart`} cx="38%" cy="30%" r="80%">
      <stop offset="0%" stopColor={B.heart0} />
      <stop offset="100%" stopColor={B.heart1} />
    </radialGradient>
    <radialGradient id={`${id}-liver`} cx="35%" cy="30%" r="85%">
      <stop offset="0%" stopColor={B.liver0} />
      <stop offset="100%" stopColor={B.liver1} />
    </radialGradient>
    <radialGradient id={`${id}-hurt`}>
      <stop offset="0%" stopColor={B.hurt} stopOpacity="0.95" />
      <stop offset="100%" stopColor={B.hurt} stopOpacity="0" />
    </radialGradient>
    <linearGradient id={`${id}-fadeg`} x1="0" y1="0" x2="0" y2="1920" gradientUnits="userSpaceOnUse">
      <stop offset="0.44" stopColor="#FFF" />
      <stop offset="0.535" stopColor="#000" />
    </linearGradient>
    <mask id={`${id}-fade`} maskUnits="userSpaceOnUse" x="0" y="0" width="1080" height="1920">
      <rect x="0" y="0" width="1080" height="1920" fill={`url(#${id}-fadeg)`} />
    </mask>
    <linearGradient id={`${id}-body`} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#3A2622" />
      <stop offset="100%" stopColor="#1A1113" />
    </linearGradient>
  </defs>
);

/** Rising steam: soft wavy ribbons that fade as they climb. `amount` 0..1. */
export const Steam: React.FC<{id: string; x: number; y: number; t: number; amount?: number; w?: number; tint?: string}> = ({id, x, y, t, amount = 1, w = 150, tint = '#FFF4E2'}) => (
  <g filter={`url(#${id}-blur-mid)`} opacity={amount}>
    {Array.from({length: 5}, (_, i) => {
      const ph = t * (0.9 + i * 0.13) + i * 1.7;
      const x0 = x + (i - 2) * (w / 5);
      const rise = ((t * 0.35 + i * 0.2) % 1) * 60;
      const d = `M ${x0} ${y - rise} C ${x0 + Math.sin(ph) * 46} ${y - 110 - rise}, ${x0 - Math.sin(ph + 1.2) * 52} ${y - 220 - rise}, ${x0 + Math.sin(ph + 2.1) * 40} ${y - 340 - rise}`;
      return <path key={i} d={d} stroke={tint} strokeWidth={16 + i * 2} fill="none" strokeLinecap="round" opacity={0.2 + 0.12 * Math.sin(ph * 1.3)} />;
    })}
  </g>
);

/** Curling cigarette smoke from a point. Puffs are born over time, rise, widen, curl and fade. `power` scales the amount. */
export const Smoke: React.FC<{id: string; x: number; y: number; t: number; seed: string; power?: number; count?: number; rise?: number; lean?: number}> = ({
  id, x, y, t, seed, power = 1, count = 90, rise = 250, lean = 0,
}) => (
  <g filter={`url(#${id}-blur-mid)`}>
    {Array.from({length: count}, (_, i) => {
      const life = 2.6 + random(`${seed}l${i}`) * 1.6;
      const age = ((t + random(`${seed}o${i}`) * life) % life) / life;
      const curl = Math.sin(age * 4 + t * 0.8 + random(`${seed}c${i}`) * 2.2) * (8 + 110 * age * age);
      const px = x + curl + lean * age * 220 + (random(`${seed}x${i}`) - 0.5) * 20;
      const py = y - age * rise * (0.8 + random(`${seed}y${i}`) * 0.5);
      return <circle key={i} cx={px} cy={py} r={7 + age * 46} fill={B.smoke} opacity={0.15 * power * Math.sin(Math.min(1, age * 1.1) * Math.PI)} />;
    })}
  </g>
);

/** Indian cutting-chai glass: ribbed glass, hot tea with a bright surface, rim highlight. Origin = glass centre. */
export const ChaiGlass: React.FC<{id: string; x: number; y: number; s?: number; tilt?: number; level?: number; hot?: number}> = ({id, x, y, s = 1, tilt = 0, level = 0.8, hot = 1}) => {
  const top = 150 - 300 * level;
  const wAt = (yy: number) => lerp(112, 78, (yy + 150) / 300);
  return (
    <g transform={`translate(${x} ${y}) rotate(${tilt}) scale(${s})`} filter={`url(#${id}-shadow)`}>
      <clipPath id={`${id}-gclip`}>
        <path d="M -112 -150 L 112 -150 L 78 142 Q 0 166 -78 142 Z" />
      </clipPath>
      <path d="M -112 -150 L 112 -150 L 78 142 Q 0 166 -78 142 Z" fill="rgba(255,255,255,0.08)" />
      <g clipPath={`url(#${id}-gclip)`}>
        <rect x={-130} y={top} width={260} height={340} fill={`url(#${id}-tea)`} />
        <rect x={-130} y={top} width={260} height={340} fill={B.teaHot} opacity={0.18 * hot} />
        <ellipse cx={0} cy={150} rx={90} ry={60} fill="#5A2C0C" opacity={0.5} />
      </g>
      <ellipse cx={0} cy={top} rx={wAt(top) - 3} ry={15} fill="#F3C27A" opacity={0.95} />
      <ellipse cx={-20} cy={top - 2} rx={wAt(top) * 0.5} ry={6} fill="#FFE7B8" opacity={0.7} />
      {[-70, -35, 0, 35, 70].map((rx, i) => (
        <path key={i} d={`M ${rx * 1.25} -120 L ${rx * 0.9} 130`} stroke="#FFFFFF" strokeWidth={5} opacity={0.1} />
      ))}
      <path d="M -112 -150 L 112 -150 L 78 142 Q 0 166 -78 142 Z" fill="none" stroke={B.glass} strokeWidth={5} strokeLinejoin="round" />
      <ellipse cx={0} cy={-150} rx={112} ry={17} fill="none" stroke="rgba(255,255,255,0.75)" strokeWidth={5} />
      <path d="M -88 -118 L -64 112" stroke="#FFFFFF" strokeWidth={12} strokeLinecap="round" opacity={0.3} />
    </g>
  );
};

/** Cigarette lying at an angle, ember at the left end. `glow` 0..1 = how hard it is being pulled. `burn` shortens it. */
export const Cigarette: React.FC<{id: string; x: number; y: number; s?: number; rot?: number; glow?: number; burn?: number; opacity?: number}> = ({id, x, y, s = 1, rot = -18, glow = 0.4, burn = 0, opacity = 1}) => {
  const tip = -190 + burn * 120;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s})`} opacity={opacity}>
      <g filter={`url(#${id}-shadow)`}>
        <rect x={tip + 14} y={-19} width={110 - tip - 14} height={38} rx={5} fill={`url(#${id}-paper)`} />
        <rect x={108} y={-19} width={92} height={38} rx={6} fill={`url(#${id}-filt)`} />
        {Array.from({length: 16}, (_, i) => (
          <circle key={i} cx={114 + random(`f${i}x`) * 80} cy={-14 + random(`f${i}y`) * 28} r={1.8} fill="#7A4313" opacity={0.6} />
        ))}
        <rect x={104} y={-19} width={5} height={38} fill="#C9A24A" />
        <path d={`M ${tip + 14} -19 L ${tip + 14} 19 L ${tip + 2} 15 L ${tip - 4} 4 L ${tip} -12 Z`} fill="#6B625C" />
        <path d={`M ${tip + 30} -19 L ${tip + 14} -19 L ${tip + 14} 19 L ${tip + 30} 19 Z`} fill="#3A2A22" opacity={0.75} />
      </g>
      <circle cx={tip + 8} cy={0} r={22 + glow * 60} fill={`url(#${id}-ember)`} opacity={0.5 + glow * 0.5} />
      <circle cx={tip + 10} cy={0} r={9 + glow * 5} fill="#FFD98A" opacity={0.6 + 0.4 * glow} />
    </g>
  );
};

// ---------- x-ray torso (front view) ----------
export const FOODPIPE: Seg[] = [
  [{x: 540, y: 392}, {x: 540, y: 440}, {x: 536, y: 520}, {x: 540, y: 600}],
  [{x: 540, y: 600}, {x: 544, y: 700}, {x: 548, y: 770}, {x: 572, y: 842}],
];
const TORSO_D =
  'M 462 452 C 462 520 330 540 230 592 C 130 646 96 780 92 1040 L 988 1040 C 984 780 950 646 850 592 C 750 540 618 520 618 452 Z';
const HEAD_D = 'M 540 150 C 640 150 672 236 668 310 C 664 392 610 462 540 462 C 470 462 416 392 412 310 C 408 236 440 150 540 150 Z';
export const HEART_D = 'M 0 -58 C -52 -128 -170 -84 -170 14 C -170 112 -62 178 0 252 C 62 178 170 112 170 14 C 170 -84 52 -128 0 -58 Z';
export const LIVER_D = 'M -230 -40 C -190 -130 -20 -150 120 -110 C 210 -84 262 -30 240 20 C 214 76 120 60 40 96 C -40 132 -120 176 -190 130 C -250 90 -256 20 -230 -40 Z';
const STOMACH_D = 'M 572 842 C 640 836 700 880 690 950 C 680 1010 610 1030 560 1004 C 530 988 540 950 560 930 C 580 908 566 880 572 842 Z';

/** Dark glass-like body with a warm rim light; organs glow inside. `show` picks what is lit: pipe / heart / liver / lungs (0..1 each). */
export const Torso: React.FC<{id: string; t: number; appear?: number; pipe?: number; hurt?: number; heart?: number; liver?: number; lungs?: number; beat?: number}> = ({
  id, t, appear = 1, pipe = 1, hurt = 0, heart = 0.35, liver = 0.25, lungs = 0.35, beat = 1.2,
}) => {
  const pulse = 1 + 0.06 * Math.max(0, Math.sin(t * Math.PI * 2 * beat)) ** 6;
  return (
    <g opacity={appear} mask={`url(#${id}-fade)`}>
      <g filter={`url(#${id}-shadow)`}>
        <path d={TORSO_D} fill={`url(#${id}-body)`} opacity={0.92} />
        <path d={HEAD_D} fill={`url(#${id}-body)`} opacity={0.92} />
      </g>
      <path d={TORSO_D} fill="none" stroke={B.rim} strokeWidth={5} opacity={0.75} />
      <path d={HEAD_D} fill="none" stroke={B.rim} strokeWidth={5} opacity={0.75} />
      <g opacity={lungs}>
        <path d="M 500 610 C 430 600 350 660 330 780 C 316 870 340 950 400 950 C 470 950 510 900 506 800 Z" fill={B.lung} opacity={0.55} />
        <path d="M 580 610 C 650 600 730 660 750 780 C 764 870 740 950 680 950 C 640 950 600 930 590 880 Z" fill={B.lung} opacity={0.55} />
        <path d="M 540 470 L 540 600 M 540 600 C 520 640 470 660 430 700 M 540 600 C 560 640 610 660 650 700" stroke="#F1C9B8" strokeWidth={14} fill="none" strokeLinecap="round" opacity={0.45} />
      </g>
      <g transform="translate(410 960) scale(0.62)" opacity={liver}>
        <path d={LIVER_D} fill={`url(#${id}-liver)`} stroke="#E8A58C" strokeWidth={4} />
      </g>
      <g opacity={pipe}>
        <path d={STOMACH_D} fill={B.pipe1} stroke={B.pipe0} strokeWidth={5} opacity={0.9} />
        <path d={`M 540 392 C 540 440 536 520 540 600 C 544 700 548 770 572 842`} stroke={B.pipeIn} strokeWidth={40} fill="none" strokeLinecap="round" />
        <path d={`M 540 392 C 540 440 536 520 540 600 C 544 700 548 770 572 842`} stroke={`url(#${id}-pipe)`} strokeWidth={28} fill="none" strokeLinecap="round" />
        {hurt > 0 ? (
          <path d={`M 540 392 C 540 440 536 520 540 600 C 544 700 548 770 572 842`} stroke={B.hurt} strokeWidth={30 + 8 * Math.sin(t * 7)} fill="none" strokeLinecap="round" opacity={hurt * (0.65 + 0.3 * Math.sin(t * 7))} filter={`url(#${id}-soft)`} />
        ) : null}
        <path d="M 498 392 C 520 410 560 410 582 392" stroke="#F4B6A0" strokeWidth={9} fill="none" strokeLinecap="round" />
      </g>
      <g transform={`translate(604 742) scale(${0.36 * pulse})`} opacity={heart}>
        <path d={HEART_D} fill={`url(#${id}-heart)`} stroke="#FFB4A6" strokeWidth={8} />
      </g>
    </g>
  );
};

/** Dots that travel down the food pipe (tea = amber drops, smoke = grey puffs). */
export const PipeFlow: React.FC<{t: number; from: number; seed: string; color: string; count?: number; r?: number; speed?: number; blur?: string}> = ({t, from, seed, color, count = 14, r = 9, speed = 0.55, blur}) => (
  <g filter={blur}>
    {Array.from({length: count}, (_, i) => {
      const st = from + (i / count) * 1.8;
      if (t < st) return null;
      const q = ((t - st) * speed) % 1.25;
      if (q > 1) return null;
      const p = along(FOODPIPE, q);
      return <circle key={i} cx={p.x + (random(`${seed}${i}`) - 0.5) * 14} cy={p.y} r={r * (0.7 + random(`${seed}r${i}`) * 0.6)} fill={color} opacity={0.9 * Math.sin(Math.min(1, q + 0.08) * Math.PI) + 0.1} />;
    })}
  </g>
);

const HookShot: React.FC<{id: string; t: number; turn: number}> = ({id, t, turn}) => {
  const k = ramp(t, turn, turn + 0.9); // 0 = still life, 1 = inside the body
  const sip = Math.sin(ramp(t, 0.15, 1.0) * Math.PI);
  const drag = Math.sin(ramp(t, 0.9, 1.9) * Math.PI);
  const gx = lerp(300, 196, k), gy = lerp(640, 300, k), gs = lerp(1.25, 0.5, k);
  const cx = lerp(770, 884, k), cy = lerp(650, 318, k), cs = lerp(1.15, 0.5, k);
  const tipX = cx - Math.cos((18 * Math.PI) / 180) * 182 * cs, tipY = cy + Math.sin((18 * Math.PI) / 180) * 182 * cs;
  return (
    <>
      <Torso id={id} t={t} appear={k} hurt={ramp(t, turn + 1.5, turn + 2.6)} heart={0.3} />
      {k > 0.5 ? (
        <>
          <path d={`M ${gx + 60} ${gy + 30} C 380 330, 480 350, 520 388`} stroke={B.teaHot} strokeWidth={9} strokeDasharray="4 22" strokeDashoffset={-t * 120} strokeLinecap="round" fill="none" opacity={(k - 0.5) * 1.8} />
          <path d={`M ${tipX} ${tipY} C 700 330, 610 350, 562 388`} stroke={B.smoke} strokeWidth={12} strokeDasharray="2 24" strokeDashoffset={-t * 100} strokeLinecap="round" fill="none" opacity={(k - 0.5) * 1.4} filter={`url(#${id}-soft)`} />
          <PipeFlow t={t} from={turn + 0.7} seed="tea" color={B.teaHot} />
          <PipeFlow t={t} from={turn + 1.0} seed="smk" color={B.smoke} r={13} speed={0.45} blur={`url(#${id}-soft)`} />
        </>
      ) : null}
      <circle cx={gx} cy={gy} r={300 * gs} fill={`url(#${id}-glow)`} opacity={0.2} />
      <Steam id={id} x={gx} y={gy - 150 * gs} t={t} amount={1 - k * 0.55} w={150 * gs} />
      <ChaiGlass id={id} x={gx} y={gy} s={gs} tilt={-13 * sip * (1 - k)} />
      <Smoke id={id} x={tipX} y={tipY} t={t} seed="hook" power={(0.75 + drag * 0.6) * (1 - k * 0.5)} rise={lerp(330, 150, k)} lean={-0.15} />
      <Cigarette id={id} x={cx} y={cy} s={cs} glow={0.35 + 0.65 * drag + 0.1 * Math.sin(t * 9)} />
    </>
  );
};

export const BodyScene: React.FC<BodyProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const t = sec(frame, fps);
  const u = unit(width, height);
  const id = `b${p.shot}`;
  const H = p.headline_at_s ?? 0.25;
  const turn = p.turn_at_s ?? 3.4;
  const push = 1 + 0.07 * (frame / Math.max(1, durationInFrames)); // slow push-in, like the reference
  let art: React.ReactNode = null;
  if (p.shot === 'hook') art = <HookShot id={id} t={t} turn={turn} />;
  else art = shotArt(p, id, t);
  const two = p.headline2 !== undefined;
  const swap = two ? ramp(t, turn - 0.1, turn + 0.25) : 0;
  return (
    <AbsoluteFill style={{backgroundColor: C.bg0}}>
      <svg viewBox="0 0 1080 1920" width={width} height={height} preserveAspectRatio="xMidYMid slice" style={{position: 'absolute', inset: 0}}>
        <Defs id={id} />
        <BodyDefs id={id} />
        <Backdrop id={id} t={t} seed={p.shot} />
        <g transform={`translate(540 760) scale(${1.12 * push}) translate(-540 -640)`}>{art}</g>
      </svg>
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(14,9,10,0) 54%, rgba(14,9,10,0.72) 68%, rgba(14,9,10,0.86) 100%)'}} />
      {(p.chips ?? []).map((c, i) => {
        const pos = [[272, 215], [808, 215], [272, 1130], [808, 1130]][i % 4];
        return <Pill key={i} text={c.text} x={pos[0]} y={pos[1]} t={t} at={c.at_s} u={u} />;
      })}
      {p.big ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: 300 * u, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 132 * u, color: C.arrow,
          opacity: ramp(t, p.big_at_s ?? 0, (p.big_at_s ?? 0) + 0.3), textShadow: `0 ${6 * u}px ${30 * u}px rgba(0,0,0,0.9)`, letterSpacing: -2 * u}}>
          {p.count_to !== undefined ? `${Math.round(p.count_to * ramp(t, p.big_at_s ?? 0, (p.big_at_s ?? 0) + 1.6)).toLocaleString(p.locale ?? 'en-US')}${p.count_suffix ?? ''}` : p.big}
        </div>
      ) : null}
      {p.badge ? <Pill text={p.badge} x={540} y={1170} t={t} at={p.badge_at_s ?? 0} u={u} color={B.good} /> : null}
      <div style={{opacity: 1 - swap}}><Headline text={p.headline} at={H} t={t} u={u} top={1240} /></div>
      {two ? <div style={{opacity: swap}}><Headline text={p.headline2} at={turn} t={t} u={u} top={1240} /></div> : null}
      {p.sub ? (
        <div style={{position: 'absolute', left: 80 * u, right: 80 * u, top: 1360 * u, textAlign: 'center', fontFamily: FONT, fontWeight: 700, fontSize: 44 * u, color: '#F3DCC2',
          opacity: ramp(t, p.sub_at_s ?? H + 0.4, (p.sub_at_s ?? H + 0.4) + 0.3), textShadow: `0 ${4 * u}px ${18 * u}px rgba(0,0,0,0.9)`}}>
          {p.sub}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
