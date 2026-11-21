// Shots after the hook: macro food pipe (scald, smoke settling), study numbers, heart, liver, cool-down, end.
import React from 'react';
import {random} from 'remotion';
import {C, FONT, FlowArrows, ramp, lerp} from './MedScene';
import type {Seg} from './MedScene';
import {B, ChaiGlass, Cigarette, HEART_D, LIVER_D, Smoke, Steam, Torso} from './BodyScene';
import type {BodyProps} from './BodyScene';
import {donateArt} from './DonateShots';
import {spicyArt} from './SpicyShots';
import {coldArt} from './ColdShots';

const TX = 470; // macro tube centre
const wall = (side: -1 | 1, half: number, t: number, wob = 14) => {
  const pts: string[] = [];
  for (let y = -80; y <= 1560; y += 40) pts.push(`${TX + side * (half + Math.sin(y * 0.011 + t * 1.3 + (side > 0 ? 1.4 : 0)) * wob)} ${y}`);
  return pts;
};
const band = (side: -1 | 1, a: number, b: number, t: number) => `M ${wall(side, a, t).join(' L ')} L ${wall(side, b, t).reverse().join(' L ')} Z`;
const edge = (side: -1 | 1, half: number, t: number) => `M ${wall(side, half, t).join(' L ')}`;

/** Big cut-open food pipe: muscle rings outside, wet pink lining inside, dark lumen. `heat` 0..1 reddens the lining down to heatY. */
const Tube: React.FC<{id: string; t: number; heat?: number; heatY?: number}> = ({id, t, heat = 0, heatY = 1200}) => (
  <g>
    <g filter={`url(#${id}-shadow)`}>
      <path d={band(-1, 196, 320, t)} fill="#8A3F34" />
      <path d={band(1, 196, 320, t)} fill="#8A3F34" />
    </g>
    {Array.from({length: 21}, (_, i) => {
      const y = -60 + i * 80 + ((t * 14) % 80);
      return <path key={i} d={`M ${TX - 318} ${y} q 60 22 120 0 M ${TX + 198} ${y} q 60 22 120 0`} stroke="#5E231E" strokeWidth={7} fill="none" opacity={0.55} />;
    })}
    <path d={`M ${wall(-1, 196, t).join(' L ')} L ${wall(1, 196, t).reverse().join(' L ')} Z`} fill={B.pipeIn} />
    <path d={`M ${wall(-1, 120, t, 6).join(' L ')} L ${wall(1, 120, t, 6).reverse().join(' L ')} Z`} fill="#4A1512" opacity={0.75} filter={`url(#${id}-blur-mid)`} />
    {[-1, 1].map((s) => (
      <g key={s}>
        <path d={edge(s as -1 | 1, 184, t)} stroke={B.pipe0} strokeWidth={34} fill="none" strokeLinejoin="round" />
        <clipPath id={`${id}-heat${s}`}>
          <rect x={0} y={-100} width={1080} height={heatY + 100} />
        </clipPath>
        <g clipPath={`url(#${id}-heat${s})`} opacity={heat}>
          <path d={edge(s as -1 | 1, 184, t)} stroke={B.hurt} strokeWidth={36} fill="none" />
          <path d={edge(s as -1 | 1, 172, t)} stroke="#FF8A5A" strokeWidth={30} fill="none" opacity={0.5 + 0.3 * Math.sin(t * 6)} filter={`url(#${id}-blur-mid)`} />
        </g>
        <path d={edge(s as -1 | 1, 172, t)} stroke="#FFE4D8" strokeWidth={5} fill="none" opacity={0.55} />
      </g>
    ))}
  </g>
);

const Thermo: React.FC<{x: number; y: number; h: number; level: number; label: string; mark?: number; cold?: number}> = ({x, y, h, level, label, mark = 0.65, cold = 0}) => {
  const col = cold > 0.5 ? B.cold : '#FF5136';
  return (
    <g>
      <rect x={x - 22} y={y} width={44} height={h} rx={22} fill="rgba(20,14,14,0.75)" stroke="#F4E8DC" strokeWidth={5} />
      <rect x={x - 11} y={y + h - 10 - (h - 30) * level} width={22} height={(h - 30) * level + 30} rx={11} fill={col} />
      <circle cx={x} cy={y + h + 26} r={42} fill={col} stroke="#F4E8DC" strokeWidth={5} />
      <circle cx={x - 12} cy={y + h + 14} r={10} fill="#FFFFFF" opacity={0.45} />
      {Array.from({length: 7}, (_, i) => (
        <path key={i} d={`M ${x + 24} ${y + 30 + (i * (h - 60)) / 6} h 16`} stroke="#F4E8DC" strokeWidth={4} opacity={0.7} />
      ))}
      <path d={`M ${x - 46} ${y + h - 10 - (h - 30) * mark} h 92`} stroke={C.arrow} strokeWidth={6} strokeDasharray="10 8" />
      <text x={x} y={y - 26} textAnchor="middle" fontFamily={FONT} fontWeight={900} fontSize={54} fill={C.arrow} style={{paintOrder: 'stroke'}} stroke="#120D0E" strokeWidth={8}>{label}</text>
    </g>
  );
};

const PATCHES = [{s: -1, y: 300}, {s: 1, y: 470}, {s: -1, y: 660}, {s: 1, y: 830}] as const;

const Bust: React.FC<{id: string; x: number; y: number; s?: number; lit?: number}> = ({id, x, y, s = 1, lit = 0}) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <circle cx={0} cy={-150} r={92} fill={`url(#${id}-body)`} stroke={B.rim} strokeWidth={6} />
    <path d="M -170 150 C -170 20 -90 -40 0 -40 C 90 -40 170 20 170 150 Z" fill={`url(#${id}-body)`} stroke={B.rim} strokeWidth={6} />
    <circle cx={0} cy={-20} r={230} fill={`url(#${id}-glow)`} opacity={0.35 * lit} />
  </g>
);

export const shotArt = (p: BodyProps, id: string, t: number): React.ReactNode => {
  const d = donateArt(p, id, t);
  if (d !== undefined) return d;
  const sp = spicyArt(p, id, t);
  if (sp !== undefined) return sp;
  const co = coldArt(p, id, t);
  if (co !== undefined) return co;
  if (p.shot === 'scald') {
    const front = ramp(t, 0.3, 2.2) * 1700 - 80;
    const sw = (y: number, k: number) => 104 + Math.sin(y * 0.02 - t * 5 + k) * 12;
    const ys = Array.from({length: 44}, (_, i) => -80 + i * 40).filter((y) => y <= front);
    const stream = ys.length > 1 ? `M ${ys.map((y) => `${TX - sw(y, 0)} ${y}`).join(' L ')} L ${TX} ${front + 60} L ${ys.slice().reverse().map((y) => `${TX + sw(y, 2)} ${y}`).join(' L ')} Z` : '';
    return (
      <>
        <Tube id={id} t={t} heat={ramp(t, 0.8, 2.6)} heatY={front - 60} />
        {stream ? <path d={stream} fill={`url(#${id}-tea)`} opacity={0.96} /> : null}
        {stream ? <path d={stream} fill={B.teaHot} opacity={0.25 + 0.1 * Math.sin(t * 8)} filter={`url(#${id}-blur-mid)`} /> : null}
        {Array.from({length: 12}, (_, i) => {
          const y = ((t * 520 + i * 140) % 1650) - 80;
          return y < front ? <path key={i} d={`M ${TX - 50 + (i % 4) * 34} ${y} v 70`} stroke="#FFE1A8" strokeWidth={7} strokeLinecap="round" opacity={0.45} /> : null;
        })}
        <Steam id={id} x={TX} y={Math.min(front, 900)} t={t} amount={ramp(t, 0.8, 1.6) * 0.9} w={300} />
        <Thermo x={912} y={330} h={470} level={lerp(0.3, 0.92, ramp(t, 0.4, 2.2))} label="65°C+" />
      </>
    );
  }
  if (p.shot === 'smoke_settle') {
    return (
      <>
        <Tube id={id} t={t} heat={0.55} />
        {PATCHES.map((q, i) => {
          const x = TX + q.s * 178;
          const tar = ramp(t, 1.4 + i * 0.45, 3.4 + i * 0.45);
          return (
            <g key={i}>
              <ellipse cx={x} cy={q.y} rx={62} ry={96} fill={`url(#${id}-hurt)`} opacity={0.9} />
              <ellipse cx={x} cy={q.y} rx={30 + 4 * Math.sin(t * 5 + i)} ry={62} fill="#A3160F" opacity={0.85} />
              <ellipse cx={x} cy={q.y} rx={34} ry={66} fill="#2B1A16" opacity={0.85 * tar} filter={`url(#${id}-soft)`} />
              <ellipse cx={x} cy={q.y} rx={70 + 60 * ((t * 0.7 + i * 0.3) % 1)} ry={104 + 60 * ((t * 0.7 + i * 0.3) % 1)} fill="none" stroke={B.hurt} strokeWidth={5} opacity={0.6 * (1 - ((t * 0.7 + i * 0.3) % 1))} />
            </g>
          );
        })}
        <g filter={`url(#${id}-blur-mid)`}>
          {Array.from({length: 70}, (_, i) => {
            const q = PATCHES[i % 4];
            const st = 0.2 + random(`ss${i}`) * 3.6;
            if (t < st) return null;
            const a = Math.min(1, (t - st) / 1.7);
            const e = 1 - (1 - a) ** 2;
            const x0 = TX + (random(`sx${i}`) - 0.5) * 220;
            const x = lerp(x0, TX + q.s * (150 + random(`sq${i}`) * 26), e) + Math.sin(a * 6 + i) * 34 * (1 - a);
            const y = lerp(-90, q.y + (random(`sy${i}`) - 0.5) * 120, e);
            return <circle key={i} cx={x} cy={y} r={lerp(46, 15, a)} fill={a < 1 ? B.smoke : '#6A5E58'} opacity={lerp(0.28, 0.5, a)} />;
          })}
        </g>
        <Smoke id={id} x={TX} y={150} t={t} seed="top" power={0.9} rise={-240} count={30} />
      </>
    );
  }
  if (p.shot === 'study') {
    const fill = ramp(t, 0.3, 2.2);
    const grow = ramp(t, p.turn_at_s ?? 3.2, (p.turn_at_s ?? 3.2) + 1.2);
    return (
      <>
        {Array.from({length: 9 * 20}, (_, i) => {
          const cx = 112 + (i % 20) * 45, cy = 400 + Math.floor(i / 20) * 34;
          const on = random(`p${i}`) < fill;
          const risk = on && random(`r${i}`) < grow * 0.42;
          return <circle key={i} cx={cx} cy={cy} r={11} fill={risk ? B.hurt : on ? C.arrow : '#5B4337'} opacity={on ? 0.95 : 0.5} />;
        })}
        <g opacity={ramp(t, (p.turn_at_s ?? 3.2) - 0.3, p.turn_at_s ?? 3.2)}>
          <rect x={112} y={730} width={300} height={40} rx={20} fill="#E9D9C6" />
          <rect x={112} y={820} width={300 + 300 * grow} height={40} rx={20} fill={B.hurt} />
          <text x={112} y={718} fontFamily={FONT} fontWeight={700} fontSize={34} fill="#F3DCC2">{p.labels?.[0] ?? "Neither habit"}</text>
          <text x={112} y={808} fontFamily={FONT} fontWeight={700} fontSize={34} fill="#F3DCC2">{p.labels?.[1] ?? "Burning-hot tea + daily smoking"}</text>
          <text x={440 + 300 * grow} y={856} fontFamily={FONT} fontWeight={900} fontSize={64} fill={C.arrow} opacity={grow}>≈2×</text>
        </g>
      </>
    );
  }
  if (p.shot === 'heart') {
    const ph = t * 1.15 + 0.09 * t * t; // beats, speeding up
    const beat = Math.max(0, Math.sin(ph * Math.PI * 2)) ** 5;
    const ecg = (x: number) => {
      const q = ((x / 250 - ph) % 1 + 1) % 1;
      return q < 0.06 ? -30 * Math.sin((q / 0.06) * Math.PI) : q < 0.1 ? 60 : q < 0.14 ? -190 : q < 0.18 ? 90 : q < 0.3 ? -40 * Math.sin(((q - 0.18) / 0.12) * Math.PI) : 0;
    };
    const line = `M ${Array.from({length: 121}, (_, i) => `${60 + i * 8} ${905 + ecg(60 + i * 8) * 0.55}`).join(' L ')}`;
    return (
      <>
        <Torso id={id} t={t} appear={0.4} heart={0} pipe={0.3} lungs={0.25} />
        <circle cx={540} cy={560} r={330 + beat * 40} fill={`url(#${id}-hurt)`} opacity={0.22 + beat * 0.2} />
        <g transform={`translate(540 500) scale(${1.32 + beat * 0.1})`} filter={`url(#${id}-shadow)`}>
          <path d="M -40 -70 C -60 -170 -10 -220 30 -230 M 30 -80 C 40 -170 100 -200 150 -190" stroke="#C2463A" strokeWidth={46} fill="none" strokeLinecap="round" />
          <path d="M -90 -50 C -120 -120 -110 -170 -90 -200" stroke={C.vein} strokeWidth={38} fill="none" strokeLinecap="round" />
          <path d={HEART_D} fill={`url(#${id}-heart)`} stroke="#FFB4A6" strokeWidth={6} />
          <path d="M -30 0 C -70 60 -40 140 0 200 M 40 -10 C 90 40 80 110 50 160" stroke="#7A1614" strokeWidth={8} fill="none" opacity={0.7} strokeLinecap="round" />
          <ellipse cx={-80} cy={-20} rx={34} ry={54} fill="#FFFFFF" opacity={0.16} />
        </g>
        <path d={line} stroke={C.arrow} strokeWidth={14} fill="none" opacity={0.35} filter={`url(#${id}-soft)`} strokeLinejoin="round" />
        <path d={line} stroke={C.arrow} strokeWidth={6} fill="none" strokeLinejoin="round" />
      </>
    );
  }
  if (p.shot === 'liver') {
    const speed = 0.5 + 0.9 * ramp(t, 0.8, 4.5); // caffeine is cleared faster and faster
    const feed: Seg[] = [[{x: -40, y: 300}, {x: 160, y: 300}, {x: 250, y: 420}, {x: 420, y: 500}]];
    return (
      <>
        <circle cx={540} cy={540} r={360} fill={`url(#${id}-ember)`} opacity={0.1 + 0.14 * ramp(t, 0.8, 3) * (0.7 + 0.3 * Math.sin(t * 11))} />
        <g transform="translate(540 540) scale(1.55)" filter={`url(#${id}-shadow)`}>
          <path d={LIVER_D} fill={`url(#${id}-liver)`} stroke="#E8A58C" strokeWidth={4} />
          <path d="M 40 -120 C 30 -40 40 30 44 96" stroke="#5A1F18" strokeWidth={6} fill="none" opacity={0.6} />
          <ellipse cx={-90} cy={-50} rx={90} ry={34} fill="#FFFFFF" opacity={0.12} transform="rotate(-16)" />
          <path d="M 60 70 C 80 110 120 120 150 100" stroke="#6FA04A" strokeWidth={22} strokeLinecap="round" fill="none" opacity={0.85} />
        </g>
        {Array.from({length: 22}, (_, i) => {
          const q = (t * speed * 0.5 + i / 22) % 1;
          const a = q / 0.7;
          if (a > 1) {
            const f = (q - 0.7) / 0.3;
            return <circle key={i} cx={430 + random(`lx${i}`) * 240} cy={470 + random(`ly${i}`) * 150} r={12 + f * 40} fill={`url(#${id}-ember)`} opacity={1 - f} />;
          }
          const px = lerp(feed[0][0].x, 430 + random(`lx${i}`) * 240, a), py = lerp(300, 470 + random(`ly${i}`) * 150, a * a) + Math.sin(a * 9 + i) * 14;
          return <circle key={i} cx={px} cy={py} r={13} fill="#8A4A16" stroke="#F3C27A" strokeWidth={4} />;
        })}
        {Array.from({length: 4}, (_, i) => { const k = ramp(t, (p.turn_at_s ?? 2.6) + i * 0.45, (p.turn_at_s ?? 2.6) + i * 0.45 + 0.25); return k > 0 ? <ChaiGlass key={i} id={`${id}c${i}`} x={225 + i * 210} y={930} s={0.52 * k} /> : null; })}
      </>
    );
  }
  if (p.shot === 'cool') {
    const cool = ramp(t, 0.4, 2.6);
    const turn = p.turn_at_s ?? 2.8;
    const drop = ramp(t, turn + 0.35, turn + 1.1);
    const cross = ramp(t, turn, turn + 0.3);
    const heal = ramp(t, turn + 1.0, turn + 1.9);
    return (
      <>
        <circle cx={300} cy={600} r={340} fill={`url(#${id}-glow)`} opacity={0.18} />
        <Steam id={id} x={300} y={420} t={t} amount={1 - cool * 0.85} w={170} />
        <ChaiGlass id={id} x={300} y={610} s={1.2} hot={1 - cool} />
        <Thermo x={520} y={390} h={380} level={lerp(0.92, 0.42, cool)} label={p.labels?.[0] ?? "Let it cool"} cold={cool} />
        <g opacity={1 - heal}>
          <Smoke id={id} x={690} y={690} t={t} seed="cool" power={1 - cross} rise={300} count={30} />
          <Cigarette id={id} x={850} y={630 + drop * drop * 620} rot={-18 + drop * 70} glow={0.4 * (1 - cross)} opacity={1 - drop} />
          <g opacity={cross * (1 - drop)} stroke={B.hurt} strokeWidth={22} strokeLinecap="round">
            <path d={`M 720 500 L ${720 + 260 * cross} ${500 + 260 * cross}`} />
            <path d={`M 980 500 L ${980 - 260 * cross} ${500 + 260 * cross}`} />
          </g>
        </g>
        <g transform="translate(560 300) scale(0.56)" opacity={heal}>
          <circle cx={540} cy={640} r={420} fill={B.good} opacity={0.12 + 0.05 * Math.sin(t * 3)} filter={`url(#${id}-blur-far)`} />
          <Torso id={id} t={t} hurt={0} heart={0.5} />
          <path d="M 540 392 C 540 440 536 520 540 600 C 544 700 548 770 572 842" stroke={B.good} strokeWidth={44} fill="none" strokeLinecap="round" opacity={0.45 + 0.2 * Math.sin(t * 4)} filter={`url(#${id}-soft)`} />
        </g>
      </>
    );
  }
  if (p.shot === 'end') {
    const arc: Seg[] = [[{x: 330, y: 470}, {x: 440, y: 330}, {x: 640, y: 330}, {x: 750, y: 470}]];
    return (
      <>
        <Bust id={id} x={270} y={700} s={1.05} />
        <Bust id={id} x={810} y={700} s={1.05} lit={ramp(t, 0.9, 1.5)} />
        <FlowArrows segs={arc} t={t * 2.2} count={3} size={40} appear={ramp(t, 0.3, 0.7)} />
        <ChaiGlass id={id} x={742} y={880} s={0.34} />
        <Cigarette id={id} x={872} y={890} s={0.42} glow={0.5 + 0.3 * Math.sin(t * 6)} />
        <Smoke id={id} x={796} y={870} t={t} seed="end" power={0.7} rise={170} count={18} />
      </>
    );
  }
  return null;
};
