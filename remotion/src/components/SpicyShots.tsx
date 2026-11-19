// Spicy-food explainer shots in the "realistic upgrade" look: lit, textured, glossy materials (SVG lighting filters),
// macro depth, bokeh. Same drawn-anatomy pipeline as BodyShots, no photo/stock files. Deterministic (seeded).
// Art area (after the 1.12 zoom in BodyScene) is design x 120..960, y 0..880.
import React from 'react';
import {random} from 'remotion';
import {C, FONT, ramp, lerp} from './MedScene';
import type {BodyProps} from './BodyScene';

const YEL = C.arrow;
const ORANGE = '#FF8A1F', CHILI0 = '#FF5436', CHILI1 = '#8E0F0A', MILK = '#F7F4EC', NERVE = '#7DE7FF', CALC = '#FFE066';
const ease = (q: number) => 1 - (1 - Math.min(1, Math.max(0, q))) ** 3;
const txt = (x: number, y: number, s: string, size: number, fill = '#F3DCC2', anchor: 'start' | 'middle' | 'end' = 'middle', w = 800) => (
  <text x={x} y={y} textAnchor={anchor} fontFamily={FONT} fontWeight={w} fontSize={size} fill={fill} stroke="#120D0E" strokeWidth={size * 0.16} style={{paintOrder: 'stroke'}}>{s}</text>
);

/** Lighting filters shared by the realistic shots: wet tissue (bump texture + specular), glossy plastic/skin, soft grain. */
export const RealDefs: React.FC<{id: string}> = ({id}) => (
  <defs>
    <filter id={`${id}-flesh`} x="-5%" y="-5%" width="110%" height="110%" colorInterpolationFilters="sRGB">
      <feTurbulence type="fractalNoise" baseFrequency="0.03 0.045" numOctaves="4" seed="7" result="n" />
      <feDiffuseLighting in="n" lightingColor="#FFE2D0" surfaceScale="2.4" diffuseConstant="1.15" result="d">
        <feDistantLight azimuth="235" elevation="58" />
      </feDiffuseLighting>
      <feComposite in="d" in2="SourceAlpha" operator="in" result="dl" />
      <feBlend in="SourceGraphic" in2="dl" mode="multiply" result="m" />
      <feGaussianBlur in="SourceAlpha" stdDeviation="5" result="b" />
      <feSpecularLighting in="b" surfaceScale="6" specularConstant="1.1" specularExponent="26" lightingColor="#FFFFFF" result="s">
        <fePointLight x="330" y="120" z="260" />
      </feSpecularLighting>
      <feComposite in="s" in2="SourceAlpha" operator="in" result="sl" />
      <feComposite in="m" in2="sl" operator="arithmetic" k1="0" k2="1" k3="0.7" k4="0" />
    </filter>
    <filter id={`${id}-gloss`} x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="sRGB">
      <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="b" />
      <feSpecularLighting in="b" surfaceScale="5" specularConstant="1.3" specularExponent="38" lightingColor="#FFFFFF" result="s">
        <fePointLight x="300" y="60" z="300" />
      </feSpecularLighting>
      <feComposite in="s" in2="SourceAlpha" operator="in" result="sl" />
      <feComposite in="SourceGraphic" in2="sl" operator="arithmetic" k1="0" k2="1" k3="0.85" k4="0" />
    </filter>
    <filter id={`${id}-grain`} x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" />
      <feColorMatrix values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.35 0" />
    </filter>
    <radialGradient id={`${id}-chili`} cx="30%" cy="25%" r="85%">
      <stop offset="0%" stopColor="#FF8A5E" />
      <stop offset="35%" stopColor={CHILI0} />
      <stop offset="100%" stopColor={CHILI1} />
    </radialGradient>
    <radialGradient id={`${id}-stem`} cx="40%" cy="30%" r="80%">
      <stop offset="0%" stopColor="#8FD35A" />
      <stop offset="100%" stopColor="#2F6A1C" />
    </radialGradient>
    <linearGradient id={`${id}-tongue`} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stopColor="#E98A86" />
      <stop offset="100%" stopColor="#A83F45" />
    </linearGradient>
    <radialGradient id={`${id}-brain`} cx="40%" cy="30%" r="80%">
      <stop offset="0%" stopColor="#F4B6B0" />
      <stop offset="60%" stopColor="#D9807F" />
      <stop offset="100%" stopColor="#8E3B44" />
    </radialGradient>
    <radialGradient id={`${id}-dropw`} cx="35%" cy="30%" r="75%">
      <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
      <stop offset="45%" stopColor="#9EDCFF" stopOpacity="0.75" />
      <stop offset="100%" stopColor="#2E7FB8" stopOpacity="0.8" />
    </radialGradient>
    <radialGradient id={`${id}-oil`} cx="35%" cy="30%" r="75%">
      <stop offset="0%" stopColor="#FFE3A0" />
      <stop offset="50%" stopColor={ORANGE} />
      <stop offset="100%" stopColor="#B04A00" />
    </radialGradient>
    <radialGradient id={`${id}-prot`} cx="35%" cy="30%" r="80%">
      <stop offset="0%" stopColor="#C7A6FF" />
      <stop offset="100%" stopColor="#4B2C9A" />
    </radialGradient>
    <radialGradient id={`${id}-lipid`} cx="35%" cy="30%" r="80%">
      <stop offset="0%" stopColor="#FFE9C9" />
      <stop offset="100%" stopColor="#C98A5A" />
    </radialGradient>
    <linearGradient id={`${id}-milk`} x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stopColor="#D9D4C8" />
      <stop offset="45%" stopColor="#FFFFFF" />
      <stop offset="100%" stopColor="#CFC9BC" />
    </linearGradient>
    <linearGradient id={`${id}-glass`} x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stopColor="rgba(255,255,255,0.45)" />
      <stop offset="50%" stopColor="rgba(255,255,255,0.08)" />
      <stop offset="100%" stopColor="rgba(255,255,255,0.4)" />
    </linearGradient>
  </defs>
);

/** Glossy red chilli. Origin = stem joint, body points to the right and curls down. */
const Chili: React.FC<{id: string; x: number; y: number; s?: number; rot?: number; o?: number}> = ({id, x, y, s = 1, rot = 0, o = 1}) => (
  <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s})`} opacity={o} filter={`url(#${id}-shadow)`}>
    <g filter={`url(#${id}-gloss)`}>
      <path d="M 0 -34 C 90 -64 230 -30 330 60 C 380 106 400 170 380 230 C 330 212 262 170 190 122 C 110 70 40 48 0 36 Z" fill={`url(#${id}-chili)`} />
    </g>
    <path d="M 20 -22 C 110 -44 220 -14 300 52" stroke="#FFFFFF" strokeWidth={9} fill="none" strokeLinecap="round" opacity={0.5} />
    <path d="M 0 -34 C -26 -52 -36 -8 -12 36 C 6 44 14 8 0 -34 Z" fill={`url(#${id}-stem)`} />
    <path d="M -22 -30 C -50 -70 -80 -66 -96 -86" stroke="#3E7D26" strokeWidth={16} fill="none" strokeLinecap="round" />
  </g>
);

const Beacon: React.FC<{id: string; x: number; y: number; t: number; s?: number; on?: number}> = ({id, x, y, t, s = 1, on = 1}) => {
  const blink = 0.55 + 0.45 * Math.sin(t * 11);
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <circle r={190} fill="#FF2A1F" opacity={0.28 * blink * on} filter={`url(#${id}-blur-mid)`} />
      <g transform={`rotate(${t * 380})`} opacity={0.55 * on}>
        <path d="M 0 0 L 300 -46 L 300 46 Z" fill="#FF5A44" filter={`url(#${id}-blur-mid)`} />
        <path d="M 0 0 L -300 -46 L -300 46 Z" fill="#FF5A44" filter={`url(#${id}-blur-mid)`} />
      </g>
      <rect x={-72} y={26} width={144} height={30} rx={8} fill="#2B2B2F" />
      <path d="M -62 30 C -62 -50 62 -50 62 30 Z" fill={blink > 0.6 ? '#FF3A2C' : '#8E1913'} stroke="#FFB0A6" strokeWidth={4} />
      <ellipse cx={-22} cy={-8} rx={14} ry={22} fill="#FFFFFF" opacity={0.45} transform="rotate(20 -22 -8)" />
    </g>
  );
};

const Drop: React.FC<{id: string; x: number; y: number; s?: number; o?: number}> = ({id, x, y, s = 1, o = 1}) => (
  <g transform={`translate(${x} ${y}) scale(${s})`} opacity={o}>
    <path d="M 0 -34 C 18 -6 26 8 26 20 C 26 36 14 46 0 46 C -14 46 -26 36 -26 20 C -26 8 -18 -6 0 -34 Z" fill={`url(#${id}-dropw)`} stroke="#E8F6FF" strokeWidth={2.5} />
    <ellipse cx={-8} cy={12} rx={5} ry={10} fill="#FFFFFF" opacity={0.85} />
  </g>
);

const Capsaicin: React.FC<{x: number; y: number; s?: number; rot?: number; o?: number; glow?: number}> = ({x, y, s = 1, rot = 0, o = 1, glow = 0.6}) => (
  <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${s})`} opacity={o}>
    <circle r={46} fill={ORANGE} opacity={0.35 * glow} />
    <path d="M -22 -12 L -11 -31 L 11 -31 L 22 -12 L 11 7 L -11 7 Z" fill="#FFB347" stroke="#FFE3A0" strokeWidth={3} />
    <path d="M 11 7 L 36 28 L 62 18 L 88 38" stroke={ORANGE} strokeWidth={7} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx={-26} cy={-30} r={7} fill="#FFFFFF" opacity={0.75} />
  </g>
);

const Brain: React.FC<{id: string; x: number; y: number; s?: number; red?: number; calm?: number; t: number}> = ({id, x, y, s = 1, red = 0, calm = 0, t}) => {
  const sulci = Array.from({length: 16}, (_, i) => {
    const a = random(`bs${i}a`) * Math.PI * 2, r = 20 + random(`bs${i}r`) * 150;
    const cx = Math.cos(a) * r * 1.35, cy = Math.sin(a) * r * 0.8 - 6;
    return `M ${cx - 30} ${cy - 8} q 18 -22 34 -2 t 36 6`;
  });
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} filter={`url(#${id}-shadow)`}>
      <circle r={290} fill="#FF2A1F" opacity={0.3 * red * (0.6 + 0.4 * Math.sin(t * 12))} filter={`url(#${id}-blur-mid)`} />
      <circle r={290} fill="#3BE8B8" opacity={0.2 * calm} filter={`url(#${id}-blur-mid)`} />
      <g filter={`url(#${id}-flesh)`}>
        <path d="M -250 20 C -270 -110 -150 -190 -20 -178 C 90 -196 240 -150 252 -20 C 270 90 190 168 70 160 C 40 220 -40 214 -70 160 C -180 168 -240 120 -250 20 Z" fill={`url(#${id}-brain)`} />
      </g>
      <path d="M 0 -178 C 18 -80 -12 60 6 168" stroke="#7A2F38" strokeWidth={9} fill="none" strokeLinecap="round" opacity={0.7} />
      {sulci.map((d, i) => <path key={i} d={d} stroke="#8B3A42" strokeWidth={7} fill="none" strokeLinecap="round" opacity={0.6} />)}
      <path d="M -170 -110 C -80 -150 20 -150 90 -120" stroke="#FFFFFF" strokeWidth={8} fill="none" strokeLinecap="round" opacity={0.35} />
    </g>
  );
};

const Tongue: React.FC<{id: string; y0: number; t: number}> = ({id, y0, t}) => (
  <g>
    <g filter={`url(#${id}-flesh)`}>
      <path d={`M 80 ${y0 + 40} C 220 ${y0 - 30} 860 ${y0 - 30} 1000 ${y0 + 40} L 1000 1000 L 80 1000 Z`} fill={`url(#${id}-tongue)`} />
    </g>
    {Array.from({length: 120}, (_, i) => {
      const x = 130 + random(`pp${i}x`) * 820, y = y0 + 10 + random(`pp${i}y`) * 260;
      const r = 5 + random(`pp${i}r`) * 7;
      return (
        <g key={i}>
          <circle cx={x} cy={y} r={r} fill="#F4A9A2" />
          <circle cx={x - r * 0.3} cy={y - r * 0.35} r={r * 0.35} fill="#FFFFFF" opacity={0.7} />
        </g>
      );
    })}
    <path d={`M 540 ${y0 + 10} C 548 ${y0 + 90} 532 ${y0 + 190} 540 ${y0 + 300}`} stroke="#7E2C33" strokeWidth={9} fill="none" strokeLinecap="round" opacity={0.6} />
  </g>
);

const hook = (p: BodyProps, id: string, t: number) => {
  const drop = ease(t / 0.8), bob = Math.sin(t * 3) * 10;
  return (
    <>
      <Tongue id={id} y0={560} t={t} />
      <Chili id={id} x={lerp(260, 290, drop)} y={lerp(-60, 260 + bob, drop)} s={1.05} rot={lerp(-40, -8, drop)} />
      <Beacon id={id} x={800} y={230} t={t} s={1.15} on={ramp(t, 0.9, 1.3)} />
      {txt(540, 150, 'FIRE ALARM?!', 84, YEL, 'middle', 900)}
    </>
  );
};

const sensor = (p: BodyProps, id: string, t: number) => {
  const turn = p.turn_at_s ?? 3.2;
  const dock = ease((t - 0.8) / (turn - 0.8)), open = ease((t - turn) / 0.5);
  const heads = Array.from({length: 22}, (_, i) => 130 + i * 40);
  const gap = (x: number) => Math.abs(x - 540) < 70;
  return (
    <>
      <rect x={100} y={0} width={880} height={380} fill="#C98A7A" opacity={0.18} />
      <rect x={100} y={500} width={880} height={400} fill="#1B0F2B" opacity={0.55} />
      {txt(150, 70, 'ZABAAN KI SURFACE', 28, '#F3DCC2', 'start')}
      {txt(150, 560, 'NERVE KE ANDAR', 28, '#BFA8FF', 'start')}
      {heads.map((x, i) => !gap(x) && (
        <g key={i}>
          <path d={`M ${x} 400 v 40 M ${x + 10} 400 v 36`} stroke="#C98A5A" strokeWidth={6} strokeLinecap="round" />
          <circle cx={x} cy={382} r={18} fill={`url(#${id}-lipid)`} />
          <path d={`M ${x} 480 v -40 M ${x + 10} 480 v -36`} stroke="#C98A5A" strokeWidth={6} strokeLinecap="round" />
          <circle cx={x} cy={498} r={18} fill={`url(#${id}-lipid)`} />
        </g>
      ))}
      <g filter={`url(#${id}-gloss)`}>
        <path d={`M 450 350 C 450 330 530 330 530 360 L 530 520 C 530 540 450 540 450 515 Z`} transform={`translate(${-open * 26} 0)`} fill={`url(#${id}-prot)`} />
        <path d={`M 550 350 C 550 330 630 330 630 360 L 630 520 C 630 540 550 540 550 515 Z`} transform={`translate(${open * 26} 0)`} fill={`url(#${id}-prot)`} />
      </g>
      {txt(540, 310, 'TRPV1 SENSOR', 40, '#E4D6FF', 'middle', 800)}
      {Array.from({length: 7}, (_, i) => {
        const dx = 150 + (i % 4) * 190 + Math.sin(t * 1.4 + i) * 22, dy = 130 + Math.floor(i / 4) * 120 + Math.cos(t * 1.2 + i) * 18;
        if (i === 0) return <Capsaicin key={i} x={lerp(dx, 540, dock)} y={lerp(dy, 345, dock)} s={1.1} rot={lerp(-20, 90, dock)} />;
        return <Capsaicin key={i} x={dx} y={dy} s={0.8} rot={20 * i} o={0.85} />;
      })}
      {open > 0 && Array.from({length: 14}, (_, i) => {
        const q = ((t - turn) * 0.8 + i / 14) % 1;
        return <circle key={i} cx={540 + (random(`ca${i}`) - 0.5) * 70} cy={380 + q * 300} r={9} fill={CALC} opacity={Math.sin(q * Math.PI) * 0.95} />;
      })}
      {open > 0 && (
        <>
          <path d="M 540 640 C 540 700 540 760 540 880" stroke={NERVE} strokeWidth={14} fill="none" opacity={0.5 * open} filter={`url(#${id}-blur-mid)`} />
          {Array.from({length: 4}, (_, i) => <circle key={i} cx={540} cy={650 + ((((t - turn) * 220 + i * 70) % 260) + 260) % 260} r={13} fill={NERVE} opacity={0.9 * open} />)}
          {txt(540, 860, 'ALARM SIGNAL → BRAIN', 36, NERVE, 'middle', 800)}
        </>
      )}
    </>
  );
};

const degree = (p: BodyProps, id: string, t: number) => {
  const cnt = Math.round(43 * ease((t - 0.3) / 1.6));
  const y43 = 760 - 43 * 9.5, y25 = 760 - 25 * 9.5;
  return (
    <>
      <g transform="translate(320 0)">
        <rect x={-34} y={90} width={68} height={700} rx={34} fill="rgba(255,255,255,0.12)" stroke="#E8F2FF" strokeWidth={5} />
        <circle cx={0} cy={800} r={64} fill="rgba(255,255,255,0.12)" stroke="#E8F2FF" strokeWidth={5} />
        <circle cx={0} cy={800} r={48} fill="#E5332A" />
        <rect x={-14} y={y25 + Math.sin(t * 3) * 2} width={28} height={800 - y25} fill="#E5332A" />
        {[0, 10, 20, 30, 40, 50, 60].map((d) => (
          <g key={d}>
            <path d={`M 34 ${760 - d * 9.5} h 20`} stroke="#E8F2FF" strokeWidth={4} />
            {txt(98, 774 - d * 9.5, `${d}°`, 30, '#E8F2FF', 'middle', 700)}
          </g>
        ))}
        <path d={`M -90 ${y43} H 150`} stroke={YEL} strokeWidth={7} strokeDasharray="18 12" />
        <path d={`M -80 ${y25} h -30`} stroke="#9EDCFF" strokeWidth={5} />
        {txt(-118, y25 + 10, 'MIRCHI', 26, '#9EDCFF', 'end', 800)}
      </g>
      <Beacon id={id} x={650} y={y43 + 20} t={t} s={0.8} on={ramp(t, 2.0, 2.4)} />
      {txt(760, 190, `${cnt}°C`, 128, YEL, 'middle', 900)}
      {txt(760, 250, 'ALARM LINE', 44, '#F4EFC6', 'middle', 800)}
      <Chili id={id} x={640} y={y25 + 60} s={0.5} rot={-6} />
      {ramp(t, 2.4, 2.8) > 0 && <>{txt(780, y25 - 40, 'GARMI NAHI,', 32, '#FFB0A6', 'middle', 800)}{txt(780, y25 - 4, 'FIR BHI ALARM!', 32, '#FFB0A6', 'middle', 800)}</>}
    </>
  );
};

const panic = (p: BodyProps, id: string, t: number) => {
  const cols = [{x: 250, n: 'PASINA', k: 'sweat'}, {x: 540, n: 'AANKHEN', k: 'eye'}, {x: 830, n: 'NAAK', k: 'nose'}];
  return (
    <>
      <Brain id={id} x={540} y={250} s={0.95} red={1} t={t} />
      {txt(540, 60, 'AAG! AAG! AAG!', 56, '#FF6A5A', 'middle', 900)}
      {[-1, 1].map((s) => (
        <path key={s} d={`M ${540 + s * 300} 250 C ${540 + s * 360} 250 ${540 + s * 380} 280 ${540 + s * 390} 340`} stroke="#FF6A5A" strokeWidth={9} strokeLinecap="round" strokeDasharray="6 18" strokeDashoffset={-t * 100} fill="none" />
      ))}
      {cols.map((c, i) => {
        const st = 0.9 + i * 0.5;
        return (
          <g key={c.k}>
            {Array.from({length: 4}, (_, j) => {
              const q = (((t - st) * 0.7 + j / 4) % 1 + 1) % 1;
              if (t < st) return null;
              return <Drop key={j} id={id} x={c.x + (j % 2 ? 20 : -20) + Math.sin(q * 5 + j) * 8} y={470 + q * 300} s={0.7 + q * 0.5} o={Math.sin(Math.min(1, q + 0.05) * Math.PI)} />;
            })}
            <rect x={c.x - 112} y={812} width={224} height={54} rx={27} fill="rgba(15,10,12,0.8)" stroke="#FFD0C8" strokeWidth={3} opacity={ramp(t, st, st + 0.3)} />
            {txt(c.x, 852, c.n, 34, '#FFE9E4', 'middle', 800)}
          </g>
        );
      })}
    </>
  );
};

const endorphin = (p: BodyProps, id: string, t: number) => {
  const turn = p.turn_at_s ?? 1.2;
  const calm = ease((t - turn) / 1.2);
  const wave = Array.from({length: 60}, (_, i) => {
    const x = 120 + i * 14.7, a = lerp(70, 18, calm);
    const y = 700 + Math.sin(i * 0.9 + t * 7) * a * (i % 2 ? 1 : lerp(1, 0.4, calm)) * (1 - calm * 0.3);
    return `${i ? 'L' : 'M'} ${x} ${y}`;
  }).join(' ');
  return (
    <>
      <Brain id={id} x={540} y={280} s={1.0} red={1 - calm} calm={calm} t={t} />
      {Array.from({length: 30}, (_, i) => {
        const q = ((t - turn - random(`en${i}`) * 0.8) * 0.5);
        if (q <= 0) return null;
        const a = random(`ea${i}`) * Math.PI * 2, r = 120 + (q % 1) * (260 + random(`er${i}`) * 140);
        const x = 540 + Math.cos(a) * r * 1.2, y = 280 + Math.sin(a) * r * 0.85;
        return (
          <g key={i} opacity={Math.sin(Math.min(1, (q % 1) + 0.05) * Math.PI)}>
            <circle cx={x} cy={y} r={20} fill="#6CFFD8" opacity={0.25} />
            <circle cx={x} cy={y} r={10} fill="#C8FFF0" />
          </g>
        );
      })}
      <path d={wave} stroke={calm > 0.5 ? '#6CFFD8' : '#FF5A44'} strokeWidth={9} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      {txt(540, 840, calm > 0.5 ? 'ENDORPHIN: NATURAL PAINKILLER' : 'DARD SIGNAL', 38, calm > 0.5 ? '#9CFFE6' : '#FFB0A6', 'middle', 800)}
    </>
  );
};

const water = (p: BodyProps, id: string, t: number) => {
  const pour = ease((t - 0.8) / 1.0), spread = ease((t - 1.6) / 3.2);
  const blobs = Array.from({length: 9}, (_, i) => {
    const a = random(`ob${i}a`) * Math.PI * 2, d = random(`ob${i}d`) * 60;
    return {x: 540 + Math.cos(a) * d, y: 620 + Math.sin(a) * d * 0.5, a};
  });
  return (
    <>
      <Tongue id={id} y0={470} t={t} />
      {blobs.map((b, i) => (
        <ellipse key={i} cx={b.x + Math.cos(b.a) * 280 * spread} cy={b.y + Math.sin(b.a) * 95 * spread} rx={30 + 36 * spread} ry={24 + 14 * spread}
          fill={`url(#${id}-oil)`} opacity={lerp(1, 0.78, spread)} filter={`url(#${id}-gloss)`} />
      ))}
      <ellipse cx={540} cy={640} rx={lerp(60, 430, spread)} ry={lerp(30, 150, spread)} fill="#9EDCFF" opacity={0.28 * pour} />
      <g transform={`translate(330 ${lerp(-60, 120, pour)}) rotate(${lerp(0, -62, pour)})`}>
        <path d="M -90 -150 L 90 -150 L 70 160 Q 0 184 -70 160 Z" fill={`url(#${id}-glass)`} stroke="#E8F6FF" strokeWidth={5} />
        <path d="M -80 -40 L 80 -40 L 70 156 Q 0 178 -66 156 Z" fill="#7CCBFF" opacity={0.65} />
      </g>
      {pour > 0.3 && Array.from({length: 8}, (_, i) => {
        const q = (((t - 1.2) * 1.6 + i / 8) % 1 + 1) % 1;
        return <Drop key={i} id={id} x={lerp(420, 540, q)} y={lerp(210, 600, q * q)} s={0.55} o={Math.sin(q * Math.PI)} />;
      })}
      {txt(540, 120, 'TEL + PAANI = FAILA', 62, '#FFD27A', 'middle', 900)}
      {txt(540, 840, 'CAPSAICIN TEL JAISA HAI', 36, '#FFE3A0', 'middle', 800)}
    </>
  );
};

const milk = (p: BodyProps, id: string, t: number) => {
  const grab = ease((t - 1.4) / 3.4);
  const locks = [190, 365, 540, 715, 890];
  return (
    <>
      <g transform="translate(540 190)">
        <path d="M -118 -150 L 118 -150 L 92 190 Q 0 214 -92 190 Z" fill={`url(#${id}-glass)`} stroke="#F6F2E8" strokeWidth={5} />
        <path d="M -108 -70 L 108 -70 L 90 186 Q 0 208 -88 186 Z" fill={`url(#${id}-milk)`} />
        <ellipse cx={0} cy={-70} rx={108} ry={16} fill="#FFFFFF" />
        {txt(0, 100, 'DOODH', 40, '#7A6A55', 'middle', 900)}
      </g>
      {locks.map((x, i) => {
        const dx = x, dyLock = 740;
        const out = ease((t - 1.4 - i * 0.35) / 1.4);
        return (
          <g key={i}>
            <g filter={`url(#${id}-gloss)`}>
              <path d={`M ${x - 70} ${dyLock + 60} L ${x - 70} ${dyLock + 6} C ${x - 70} ${dyLock - 40} ${x - 20} ${dyLock - 40} ${x - 20} ${dyLock + 6} L ${x - 20} ${dyLock + 60} Z`} fill={`url(#${id}-prot)`} />
              <path d={`M ${x + 70} ${dyLock + 60} L ${x + 70} ${dyLock + 6} C ${x + 70} ${dyLock - 40} ${x + 20} ${dyLock - 40} ${x + 20} ${dyLock + 6} L ${x + 20} ${dyLock + 60} Z`} fill={`url(#${id}-prot)`} />
            </g>
            {out < 1 && <Capsaicin x={x} y={dyLock - 36 - out * 330} s={0.8} rot={90 + out * 60} o={1 - out * 0.4} />}
            {out > 0 && out < 1 && (
              <g transform={`translate(${x} ${dyLock - 36 - out * 330})`} opacity={0.9}>
                <circle r={46} fill="#DFF3FF" opacity={0.6} />
                <path d="M -40 -20 q -18 20 0 40 M 40 -20 q 18 20 0 40" stroke="#FFFFFF" strokeWidth={7} fill="none" strokeLinecap="round" />
              </g>
            )}
          </g>
        );
      })}
      <path d="M 120 840 H 960" stroke={grab > 0.9 ? '#7BE38B' : '#FF6A5A'} strokeWidth={8} strokeLinecap="round" opacity={0.7} />
      {txt(540, 880, grab > 0.9 ? 'CASEIN NE PAKAD KE HATA DIYA' : 'CASEIN: SABUN JAISA', 36, grab > 0.9 ? '#9CFFB2' : '#FFE3A0', 'middle', 800)}
    </>
  );
};

const endc = (p: BodyProps, id: string, t: number) => {
  const comments = ['Level 10!', 'Mild bolo, extra', 'Doodh pilao bhai', 'Sab khata hoon'];
  return (
    <>
      <Chili id={id} x={170} y={420} s={1.0} rot={-12} />
      {comments.map((c, i) => {
        const st = 0.5 + i * 0.7, q = ease((t - st) / 0.5);
        const y = lerp(880, 120 + i * 190, q);
        return (
          <g key={i} opacity={q}>
            <rect x={lerp(540, 480, q)} y={y} width={420} height={110} rx={55} fill="#F4EFC6" />
            <circle cx={lerp(540, 480, q) + 55} cy={y + 55} r={34} fill={['#E5332A', '#FF8A1F', '#7BE38B', '#8FD3FF'][i]} />
            {txt(lerp(540, 480, q) + 105, y + 68, c, 34, '#2B1A12', 'start', 800)}
          </g>
        );
      })}
    </>
  );
};

export const spicyArt = (p: BodyProps, id: string, t: number): React.ReactNode => {
  switch (p.shot) {
    case 'sp_hook': return hook(p, id, t);
    case 'sp_sensor': return sensor(p, id, t);
    case 'sp_degree': return degree(p, id, t);
    case 'sp_panic': return panic(p, id, t);
    case 'sp_endorphin': return endorphin(p, id, t);
    case 'sp_water': return water(p, id, t);
    case 'sp_milk': return milk(p, id, t);
    case 'sp_end': return endc(p, id, t);
    default: return undefined;
  }
};
