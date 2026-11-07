// Medical explainer shots (kidney / urinary tract), drawn in SVG: warm cinematic anatomy look with depth blur,
// glowing particles, crystalline stones, flexible scope, laser, DJ stent, yellow flow arrows and a bold headline.
// Everything is deterministic (seeded) so renders are repeatable. Design space: 1080 x 1920, scaled to the output.
import React from 'react';
import {AbsoluteFill, interpolate, random, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {easeOut, unit} from '../lib/anim';

type P = {x: number; y: number};
type Chip = {text: string; at_s: number};
export type MedProps = {
  shot: 'kidney_hero' | 'intro' | 'scope_path' | 'laser' | 'clearance' | 'stent' | 'big_stone' | 'factors' | 'staged' | 'end';
  headline?: string;
  headline_at_s?: number;
  sub?: string;
  sub_at_s?: number;
  break_at_s?: number; // laser: when the stone shatters
  chips?: Chip[];
  big?: string; // factors / staged: big number line
  big_at_s?: number;
  badge?: string;
  badge_at_s?: number;
  card_at_s?: number; // end: end card
  name?: string;
  role?: string;
};

const C = {
  bg0: '#1B1517', bg1: '#4A3226', bg2: '#6B3F2B',
  cortex0: '#C9775B', cortex1: '#8E4632', capsule: '#E3A58A',
  pyr0: '#B5523F', pyr1: '#6E2A22',
  urine: '#E9B949', urineDeep: '#C8902A',
  artery: '#B8382C', vein: '#3C5A96',
  stone0: '#F1E6C6', stone1: '#BFA06A', stoneEdge: '#FFF8E6',
  arrow: '#F6C431', scope: '#2A2A2E', tip: '#D6FBFF', laser: '#7DFFB8',
  stent: '#D9ECFF', white: '#FFFFFF', ink: '#120D0E',
};

// ---------- small maths ----------
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const bez = (p0: P, p1: P, p2: P, p3: P, t: number): P => {
  const u = 1 - t;
  return {
    x: u * u * u * p0.x + 3 * u * u * t * p1.x + 3 * u * t * t * p2.x + t * t * t * p3.x,
    y: u * u * u * p0.y + 3 * u * u * t * p1.y + 3 * u * t * t * p2.y + t * t * t * p3.y,
  };
};
type Seg = [P, P, P, P];
const pathD = (segs: Seg[]) =>
  `M ${segs[0][0].x} ${segs[0][0].y} ` + segs.map((s) => `C ${s[1].x} ${s[1].y} ${s[2].x} ${s[2].y} ${s[3].x} ${s[3].y}`).join(' ');
const along = (segs: Seg[], t: number): P => {
  const n = segs.length;
  const k = Math.min(n - 1, Math.floor(Math.max(0, Math.min(0.9999, t)) * n));
  return bez(...segs[k], Math.max(0, Math.min(1, t * n - k)));
};
const angleAt = (segs: Seg[], t: number) => {
  const a = along(segs, Math.max(0, t - 0.004));
  const b = along(segs, Math.min(1, t + 0.004));
  return (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI;
};
const sec = (frame: number, fps: number) => frame / fps;
const ramp = (t: number, a: number, b: number) =>
  interpolate(t, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});

// ---------- urinary tract layout (scene space) ----------
// Kidney sits upper-left of centre, ureter runs down to the bladder at the bottom.
const TRACT = {
  kidney: {x: 560, y: 560, s: 0.78},
  pelvis: {x: 480, y: 580},
  bladder: {x: 560, y: 1500},
};
const URETER: Seg[] = [
  [{x: 470, y: 600}, {x: 380, y: 700}, {x: 380, y: 880}, {x: 450, y: 1000}],
  [{x: 450, y: 1000}, {x: 520, y: 1120}, {x: 560, y: 1260}, {x: 556, y: 1420}],
];

// ---------- pieces ----------
const KIDNEY_D =
  'M 60,-260 C 190,-300 300,-200 300,0 C 300,200 190,300 60,270 C -60,245 -120,180 -110,110 C -100,60 -40,50 -40,0 C -40,-50 -100,-60 -110,-110 C -120,-180 -60,-235 60,-260 Z';
const PYR_ANGLES = [-118, -78, -38, 2, 42, 82, 122];
const PC = {x: 95, y: 0}; // pelvis centre (kidney local)
const pyrGeo = (a: number) => {
  const r = (a * Math.PI) / 180;
  const base = {x: PC.x + Math.cos(r) * 175, y: PC.y + Math.sin(r) * 225};
  const apex = {x: PC.x + Math.cos(r) * 78, y: PC.y + Math.sin(r) * 100};
  const n = {x: -Math.sin(r), y: Math.cos(r)};
  return {base, apex, n};
};

const Defs: React.FC<{id: string}> = ({id}) => (
  <defs>
    <radialGradient id={`${id}-bg`} cx="50%" cy="38%" r="75%">
      <stop offset="0%" stopColor={C.bg2} />
      <stop offset="45%" stopColor={C.bg1} />
      <stop offset="100%" stopColor={C.bg0} />
    </radialGradient>
    <radialGradient id={`${id}-cortex`} cx="65%" cy="35%" r="80%">
      <stop offset="0%" stopColor={C.cortex0} />
      <stop offset="100%" stopColor={C.cortex1} />
    </radialGradient>
    <radialGradient id={`${id}-pyr`} cx="50%" cy="20%" r="90%">
      <stop offset="0%" stopColor={C.pyr0} />
      <stop offset="100%" stopColor={C.pyr1} />
    </radialGradient>
    <linearGradient id={`${id}-stone`} x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stopColor={C.stone0} />
      <stop offset="100%" stopColor={C.stone1} />
    </linearGradient>
    <radialGradient id={`${id}-glow`}>
      <stop offset="0%" stopColor="#FFF3D6" stopOpacity="0.9" />
      <stop offset="100%" stopColor="#FFF3D6" stopOpacity="0" />
    </radialGradient>
    <radialGradient id={`${id}-tip`}>
      <stop offset="0%" stopColor={C.tip} stopOpacity="1" />
      <stop offset="100%" stopColor={C.tip} stopOpacity="0" />
    </radialGradient>
    <radialGradient id={`${id}-laser`}>
      <stop offset="0%" stopColor="#FFFFFF" stopOpacity="1" />
      <stop offset="35%" stopColor={C.laser} stopOpacity="0.9" />
      <stop offset="100%" stopColor={C.laser} stopOpacity="0" />
    </radialGradient>
    <filter id={`${id}-blur-far`} x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="34" />
    </filter>
    <filter id={`${id}-blur-mid`} x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="7" />
    </filter>
    <filter id={`${id}-soft`} x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" />
    </filter>
    <filter id={`${id}-shadow`} x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="18" stdDeviation="22" floodColor="#000" floodOpacity="0.55" />
    </filter>
  </defs>
);

/** Out-of-focus body behind everything: warm gradient, blurred vessels and organs, drifting bokeh. */
const Backdrop: React.FC<{id: string; t: number; seed: string; tint?: string}> = ({id, t, seed, tint}) => {
  const vessels = Array.from({length: 5}, (_, i) => {
    const x0 = random(`${seed}v${i}x`) * 1080;
    const red = i % 3 !== 2;
    const sway = Math.sin(t * 0.4 + i) * 20;
    return (
      <path
        key={i}
        d={`M ${x0 - 200 + sway} -100 C ${x0 + 160} 500, ${x0 - 260} 1100, ${x0 + 120 + sway} 2050`}
        stroke={red ? C.artery : C.vein}
        strokeWidth={18 + random(`${seed}v${i}w`) * 34}
        fill="none"
        opacity={0.16}
        strokeLinecap="round"
      />
    );
  });
  const blobs = Array.from({length: 8}, (_, i) => (
    <ellipse
      key={i}
      cx={random(`${seed}b${i}x`) * 1080}
      cy={random(`${seed}b${i}y`) * 1920}
      rx={140 + random(`${seed}b${i}r`) * 220}
      ry={180 + random(`${seed}b${i}q`) * 260}
      fill={i % 2 ? '#7A4A36' : '#3A2620'}
      opacity={0.45}
    />
  ));
  const bokeh = Array.from({length: 26}, (_, i) => {
    const r = 3 + random(`${seed}k${i}r`) * 9;
    const x = (random(`${seed}k${i}x`) * 1080 + t * (6 + random(`${seed}k${i}s`) * 10)) % 1080;
    const y = (random(`${seed}k${i}y`) * 1920 - t * (10 + random(`${seed}k${i}u`) * 18) + 1920 * 2) % 1920;
    return <circle key={i} cx={x} cy={y} r={r} fill="#FFE9C4" opacity={0.18 + random(`${seed}k${i}o`) * 0.3} filter={`url(#${id}-soft)`} />;
  });
  return (
    <g>
      <rect x="0" y="0" width="1080" height="1920" fill={`url(#${id}-bg)`} />
      {tint ? <rect x="0" y="0" width="1080" height="1920" fill={tint} opacity={0.18} /> : null}
      <g filter={`url(#${id}-blur-far)`}>
        {blobs}
        {vessels}
      </g>
      {bokeh}
    </g>
  );
};

/** Crystalline, spiky stone (calcium oxalate look). */
const Stone: React.FC<{id: string; x: number; y: number; r: number; seed: string; rot?: number; opacity?: number}> = ({
  id, x, y, r, seed, rot = 0, opacity = 1,
}) => {
  const n = 16;
  const pts = Array.from({length: n}, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    const rr = r * (i % 2 ? 0.62 + random(`${seed}i${i}`) * 0.18 : 0.92 + random(`${seed}o${i}`) * 0.35);
    return {x: Math.cos(a) * rr, y: Math.sin(a) * rr};
  });
  const d = pts.map((p, i) => `${i ? 'L' : 'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ') + ' Z';
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot})`} opacity={opacity}>
      <circle r={r * 1.7} fill={`url(#${id}-glow)`} opacity={0.35} />
      <path d={d} fill={`url(#${id}-stone)`} stroke={C.stoneEdge} strokeWidth={Math.max(1.5, r * 0.03)} strokeLinejoin="round" />
      {pts.map((p, i) =>
        i % 2 === 0 ? (
          <line key={i} x1={0} y1={0} x2={p.x * 0.9} y2={p.y * 0.9} stroke="#FFFFFF" strokeOpacity={0.28} strokeWidth={Math.max(1, r * 0.02)} />
        ) : null,
      )}
      <path d={`M ${-r * 0.35} ${-r * 0.45} L ${r * 0.05} ${-r * 0.6} L ${-r * 0.1} ${-r * 0.2} Z`} fill="#FFFFFF" opacity={0.55} />
    </g>
  );
};

/** Cross-section of a kidney (hilum on the left), with vessels, pyramids, pelvis and floating crystals. */
const Kidney: React.FC<{id: string; x: number; y: number; s: number; t: number; stone?: number; stoneSeed?: string; urineGlow?: number}> = ({
  id, x, y, s, t, stone = 0, stoneSeed = 'k', urineGlow = 1,
}) => {
  const pulse = 1 + Math.sin(t * 2.2) * 0.012;
  return (
    <g transform={`translate(${x} ${y}) scale(${s * pulse})`} filter={`url(#${id}-shadow)`}>
      {/* vessels into the hilum */}
      <path d="M -520 -70 C -330 -80 -170 -40 -40 -18" stroke={C.artery} strokeWidth={34} fill="none" strokeLinecap="round" />
      <path d="M -520 40 C -330 40 -170 30 -40 16" stroke={C.vein} strokeWidth={40} fill="none" strokeLinecap="round" />
      <path d={KIDNEY_D} fill={C.capsule} opacity={0.55} transform="scale(1.04) translate(-2 0)" />
      <path d={KIDNEY_D} fill={`url(#${id}-cortex)`} />
      {/* pyramids */}
      {PYR_ANGLES.map((a, i) => {
        const g = pyrGeo(a);
        const w = 58;
        const p1 = {x: g.base.x + g.n.x * w, y: g.base.y + g.n.y * w};
        const p2 = {x: g.base.x - g.n.x * w, y: g.base.y - g.n.y * w};
        return (
          <g key={i}>
            <path d={`M ${p1.x} ${p1.y} Q ${g.base.x + (g.base.x - PC.x) * 0.12} ${g.base.y + (g.base.y - PC.y) * 0.12} ${p2.x} ${p2.y} L ${g.apex.x} ${g.apex.y} Z`} fill={`url(#${id}-pyr)`} />
            {[-0.5, 0, 0.5].map((k) => (
              <line key={k} x1={g.base.x + g.n.x * w * k} y1={g.base.y + g.n.y * w * k} x2={g.apex.x} y2={g.apex.y} stroke="#E88A6E" strokeOpacity={0.35} strokeWidth={2} />
            ))}
          </g>
        );
      })}
      {/* interlobar vessels between pyramids */}
      {PYR_ANGLES.slice(0, -1).map((a, i) => {
        const g = pyrGeo(a + 20);
        return (
          <g key={i}>
            <path d={`M -30 -10 Q ${PC.x - 10} ${g.apex.y * 0.4} ${g.base.x} ${g.base.y}`} stroke={C.artery} strokeWidth={6} fill="none" opacity={0.85} />
            <path d={`M -30 10 Q ${PC.x} ${g.apex.y * 0.5} ${g.base.x * 0.97} ${g.base.y * 0.97}`} stroke={C.vein} strokeWidth={5} fill="none" opacity={0.7} />
          </g>
        );
      })}
      {/* calyces + pelvis (urine) */}
      <g opacity={0.82 * urineGlow}>
        {PYR_ANGLES.map((a, i) => {
          const g = pyrGeo(a);
          return <path key={i} d={`M ${PC.x - 20} 0 Q ${(PC.x + g.apex.x) / 2} ${g.apex.y * 0.6} ${g.apex.x} ${g.apex.y}`} stroke={C.urine} strokeWidth={30} strokeLinecap="round" fill="none" />;
        })}
        <ellipse cx={PC.x - 15} cy={6} rx={92} ry={70} fill={C.urine} />
        <path d="M 40 10 C 0 20 -30 30 -60 60" stroke={C.urine} strokeWidth={46} strokeLinecap="round" fill="none" />
      </g>
      <ellipse cx={PC.x - 30} cy={-10} rx={60} ry={34} fill="#FFF0B8" opacity={0.35} filter={`url(#${id}-soft)`} />
      {/* floating crystals */}
      {Array.from({length: 18}, (_, i) => {
        const a = random(`kc${i}a`) * Math.PI * 2 + t * 0.3;
        const rr = random(`kc${i}r`) * 70;
        return <circle key={i} cx={PC.x - 15 + Math.cos(a) * rr} cy={6 + Math.sin(a) * rr * 0.7} r={2.5 + random(`kc${i}s`) * 3} fill="#FFF6DD" opacity={0.85} />;
      })}
      {stone > 0 ? <Stone id={id} x={PC.x - 10} y={4} r={stone} seed={stoneSeed} rot={t * 6} /> : null}
      <path d={KIDNEY_D} fill="none" stroke="#F4C4AE" strokeOpacity={0.6} strokeWidth={4} />
    </g>
  );
};

const Bladder: React.FC<{x: number; y: number}> = ({x, y}) => (
  <g transform={`translate(${x} ${y})`}>
    <path d="M -190 -40 C -200 -170 200 -170 190 -40 C 180 90 80 150 0 150 C -80 150 -180 90 -190 -40 Z" fill="#B9654B" opacity={0.92} />
    <path d="M -160 -40 C -165 -140 165 -140 160 -40 C 150 70 70 120 0 120 C -70 120 -150 70 -160 -40 Z" fill={C.urine} opacity={0.55} />
    <path d="M -20 150 L -20 230 M 20 150 L 20 230" stroke="#B9654B" strokeWidth={26} strokeLinecap="round" />
  </g>
);

const Ureter: React.FC<{glow?: number}> = ({glow = 1}) => (
  <g>
    <path d={pathD(URETER)} stroke="#B9654B" strokeWidth={50} fill="none" strokeLinecap="round" />
    <path d={pathD(URETER)} stroke={C.urine} strokeWidth={24} fill="none" strokeLinecap="round" opacity={0.75 * glow} />
  </g>
);

/** Thick yellow arrows flowing along a path (direction +1 = path order, -1 = reverse). */
const FlowArrows: React.FC<{segs: Seg[]; t: number; dir?: 1 | -1; count?: number; size?: number; from?: number; to?: number; appear?: number}> = ({
  segs, t, dir = 1, count = 5, size = 46, from = 0.05, to = 0.95, appear = 1,
}) => (
  <g opacity={appear}>
    {Array.from({length: count}, (_, i) => {
      let u = (i / count + t * 0.18) % 1;
      if (dir < 0) u = 1 - u;
      const tt = lerp(from, to, u);
      const p = along(segs, tt);
      const a = angleAt(segs, tt) + (dir < 0 ? 180 : 0);
      const fade = Math.sin(u * Math.PI);
      return (
        <g key={i} transform={`translate(${p.x} ${p.y}) rotate(${a})`} opacity={fade}>
          <path
            d={`M ${-size} ${-size * 0.22} L ${size * 0.15} ${-size * 0.22} L ${size * 0.15} ${-size * 0.55} L ${size} 0 L ${size * 0.15} ${size * 0.55} L ${size * 0.15} ${size * 0.22} L ${-size} ${size * 0.22} Z`}
            fill={C.arrow}
            stroke="#8A5A00"
            strokeWidth={3}
            strokeLinejoin="round"
          />
        </g>
      );
    })}
  </g>
);

/** Flexible scope that has travelled `prog` (0..1) of a path, with a bright camera light at the tip. */
const Scope: React.FC<{id: string; segs: Seg[]; prog: number; start?: number}> = ({id, segs, prog, start = 0}) => {
  const n = 60;
  const pts = Array.from({length: n + 1}, (_, i) => along(segs, lerp(start, prog, i / n)));
  const d = pts.map((p, i) => `${i ? 'L' : 'M'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  const tip = pts[pts.length - 1];
  return prog > start ? (
    <g>
      <path d={d} stroke="#0C0C0E" strokeWidth={22} fill="none" strokeLinecap="round" opacity={0.6} />
      <path d={d} stroke={C.scope} strokeWidth={15} fill="none" strokeLinecap="round" />
      <path d={d} stroke="#9AA3AD" strokeWidth={3} fill="none" strokeLinecap="round" opacity={0.7} transform="translate(-3 -3)" />
      <circle cx={tip.x} cy={tip.y} r={70} fill={`url(#${id}-tip)`} opacity={0.75} />
      <circle cx={tip.x} cy={tip.y} r={10} fill="#FFFFFF" />
    </g>
  ) : null;
};

/** DJ stent: pigtail in the kidney pelvis, straight down the ureter, pigtail in the bladder. Drawn on with `prog`. */
const Stent: React.FC<{prog: number}> = ({prog}) => {
  const top = 'M470,600 C520,560 560,610 530,640 C500,670 450,640 470,600';
  const bottom = 'M556,1420 C600,1450 590,1500 550,1500 C510,1500 505,1450 556,1420';
  const L = 1;
  return (
    <g>
      {[pathD(URETER), top, bottom].map((d, i) => (
        <g key={i}>
          <path d={d} stroke="#0E1A26" strokeWidth={16} fill="none" strokeLinecap="round" pathLength={L} strokeDasharray={L} strokeDashoffset={L * (1 - prog)} opacity={0.55} />
          <path d={d} stroke={C.stent} strokeWidth={10} fill="none" strokeLinecap="round" pathLength={L} strokeDasharray={L} strokeDashoffset={L * (1 - prog)} />
        </g>
      ))}
    </g>
  );
};

// ---------- text ----------
const FONT = '"Inter Display", Inter, "Helvetica Neue", Arial, sans-serif';
const Headline: React.FC<{text?: string; at: number; t: number; u: number}> = ({text, at, t, u}) => {
  if (!text) return null;
  const k = ramp(t, at, at + 0.35);
  return (
    <div
      style={{
        position: 'absolute', left: 60 * u, right: 60 * u, top: 975 * u, textAlign: 'center',
        color: C.white, fontFamily: FONT, fontWeight: 900, fontSize: 92 * u, lineHeight: 1.04, letterSpacing: -1 * u,
        textShadow: `0 ${6 * u}px ${26 * u}px rgba(0,0,0,0.85), 0 0 ${4 * u}px rgba(0,0,0,0.6)`,
        whiteSpace: 'pre-line', opacity: k, transform: `translateY(${(1 - k) * 40 * u}px)`,
      }}
    >
      {text}
    </div>
  );
};

const Pill: React.FC<{text: string; x: number; y: number; t: number; at: number; u: number; color?: string; dark?: boolean}> = ({text, x, y, t, at, u, color = C.arrow, dark = true}) => {
  const k = ramp(t, at, at + 0.3);
  if (k <= 0) return null;
  return (
    <div
      style={{
        position: 'absolute', left: x * u, top: y * u, transform: `translate(-50%, -50%) scale(${0.7 + 0.3 * k})`, opacity: k,
        background: color, color: dark ? C.ink : C.white, fontFamily: FONT, fontWeight: 800, fontSize: 46 * u,
        padding: `${14 * u}px ${30 * u}px`, borderRadius: 999 * u, whiteSpace: 'nowrap',
        boxShadow: `0 ${10 * u}px ${30 * u}px rgba(0,0,0,0.45)`,
      }}
    >
      {text}
    </div>
  );
};

// ---------- shots ----------
export const MedScene: React.FC<MedProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = sec(frame, fps);
  const u = unit(width, height);
  const id = `m${p.shot}`;
  let art: React.ReactNode = null;
  let tint: string | undefined;
  const H = p.headline_at_s ?? 0.25;

  if (p.shot === 'kidney_hero' || p.shot === 'intro' || p.shot === 'end') {
    const stone = p.shot === 'end' ? 0 : 46;
    art = (
      <>
        <Kidney id={id} x={570} y={620} s={1.1} t={t} stone={stone} stoneSeed="hero" urineGlow={p.shot === 'end' ? 1.15 : 1} />
        {p.shot === 'end' ? <circle cx={600} cy={620} r={440} fill={`url(#${id}-glow)`} opacity={0.18 + 0.06 * Math.sin(t * 3)} /> : null}
      </>
    );
  }

  if (p.shot === 'scope_path' || p.shot === 'clearance' || p.shot === 'stent') {
    const k = TRACT.kidney;
    const rev: Seg[] = URETER.slice().reverse().map((s) => [s[3], s[2], s[1], s[0]] as Seg);
    const scopeIn: Seg[] = [[{x: 560, y: 1730}, {x: 560, y: 1640}, {x: 556, y: 1520}, {x: 556, y: 1420}], ...rev];
    let scopeProg = 0;
    let arrows: React.ReactNode = null;
    let extra: React.ReactNode = null;
    if (p.shot === 'scope_path') {
      scopeProg = interpolate(t, [0.4, 5.6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});
      arrows = <FlowArrows segs={URETER} t={t} dir={-1} count={4} appear={ramp(t, 0.6, 1.2)} />;
    }
    if (p.shot === 'clearance') {
      scopeProg = interpolate(t, [0, 2.6], [1, 0.55], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});
      const tip = along(scopeIn, scopeProg);
      extra = (
        <>
          {t < 2.9 ? <Stone id={id} x={tip.x + 8} y={tip.y - 14} r={16} seed="frag1" rot={t * 40} /> : null}
          {Array.from({length: 46}, (_, i) => {
            const st = 2.4 + random(`d${i}s`) * 3.6;
            if (t < st) return null;
            const q = Math.min(1, (t - st) / (2.2 + random(`d${i}v`) * 1.4));
            const pt = along(URETER, q);
            const off = (random(`d${i}o`) - 0.5) * 18;
            return <circle key={i} cx={pt.x + off} cy={pt.y} r={2.5 + random(`d${i}r`) * 3.5} fill="#FFF3D0" opacity={0.9 * (1 - q * 0.3)} />;
          })}
        </>
      );
      arrows = <FlowArrows segs={URETER} t={t} dir={1} count={5} appear={ramp(t, 2.6, 3.2)} />;
    }
    if (p.shot === 'stent') {
      extra = <Stent prog={interpolate(t, [0.3, 2.6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)})} />;
    }
    art = (
      <>
        <Bladder x={TRACT.bladder.x} y={TRACT.bladder.y} />
        <Ureter />
        <Kidney id={id} x={k.x} y={k.y} s={k.s} t={t} stone={p.shot === 'scope_path' ? 36 : 0} stoneSeed="hero" />
        <Scope id={id} segs={scopeIn} prog={scopeProg} />
        {extra}
        {arrows}
      </>
    );
  }

  if (p.shot === 'laser') {
    const br = p.break_at_s ?? 2.0;
    const broken = t >= br;
    const flash = Math.max(0, 1 - Math.abs(t - br) / 0.18);
    const beamOn = t > 0.6 && t < br + 0.25;
    const tip = {x: 230, y: 840};
    const target = {x: 610, y: 540};
    art = (
      <>
        {!broken ? <Stone id={id} x={target.x} y={target.y} r={250} seed="laser" rot={t * 3} /> : null}
        {broken
          ? Array.from({length: 34}, (_, i) => {
              const a = random(`sh${i}a`) * Math.PI * 2;
              const dist = (60 + random(`sh${i}d`) * 300) * easeOut(t, br, br + 1.2);
              return <Stone key={i} id={id} x={target.x + Math.cos(a) * dist} y={target.y + Math.sin(a) * dist} r={14 + random(`sh${i}r`) * 34} seed={`sh${i}`} rot={(t - br) * 90 * (random(`sh${i}w`) - 0.5)} />;
            })
          : null}
        {broken
          ? Array.from({length: 120}, (_, i) => {
              const a = random(`du${i}a`) * Math.PI * 2;
              const dist = (30 + random(`du${i}d`) * 420) * easeOut(t, br, br + 1.6);
              return <circle key={i} cx={target.x + Math.cos(a) * dist} cy={target.y + Math.sin(a) * dist + (t - br) * 20} r={1.5 + random(`du${i}r`) * 3} fill="#FFF3D0" opacity={0.85} />;
            })
          : null}
        <path d={`M -60 1150 C 40 1000 120 900 ${tip.x} ${tip.y}`} stroke={C.scope} strokeWidth={46} fill="none" strokeLinecap="round" />
        <path d={`M -60 1150 C 40 1000 120 900 ${tip.x} ${tip.y}`} stroke="#9AA3AD" strokeWidth={6} fill="none" opacity={0.6} transform="translate(-8 -6)" />
        <circle cx={tip.x} cy={tip.y} r={90} fill={`url(#${id}-tip)`} opacity={0.7} />
        {beamOn ? (
          <g opacity={0.75 + 0.25 * Math.sin(t * 60)}>
            <line x1={tip.x} y1={tip.y} x2={target.x} y2={target.y} stroke={C.laser} strokeWidth={26} strokeLinecap="round" opacity={0.45} filter={`url(#${id}-blur-mid)`} />
            <line x1={tip.x} y1={tip.y} x2={target.x} y2={target.y} stroke="#FFFFFF" strokeWidth={6} strokeLinecap="round" />
            <circle cx={target.x} cy={target.y} r={110} fill={`url(#${id}-laser)`} />
          </g>
        ) : null}
        <rect x={0} y={0} width={1080} height={1920} fill="#FFFFFF" opacity={flash * 0.6} />
      </>
    );
  }

  if (p.shot === 'big_stone') {
    tint = '#7A1E14';
    const shake = t < 0.5 ? Math.sin(t * 90) * 6 * (1 - t / 0.5) : 0;
    art = <Stone id={id} x={540 + shake} y={640} r={330} seed="big" rot={t * 4} />;
  }

  if (p.shot === 'factors') {
    art = <Stone id={id} x={540} y={600} r={190} seed="big" rot={t * 5} />;
  }

  if (p.shot === 'staged') {
    const cols = [270, 540, 810];
    const sizes = [92, 52, 0];
    art = (
      <>
        {cols.map((cx, i) => {
          const at = 0.5 + i * 0.9;
          const k = ramp(t, at, at + 0.4);
          return (
            <g key={i} opacity={k} transform={`translate(0 ${(1 - k) * 40})`}>
              <circle cx={cx} cy={620} r={112} fill="#2A1C18" stroke={C.arrow} strokeWidth={5} opacity={0.9} />
              {sizes[i] > 0 ? (
                <Stone id={id} x={cx} y={620} r={sizes[i]} seed="big" rot={t * 5} />
              ) : (
                <path d={`M ${cx - 55} 620 L ${cx - 15} 665 L ${cx + 60} 575`} stroke="#7BE38B" strokeWidth={22} fill="none" strokeLinecap="round" strokeLinejoin="round" />
              )}
            </g>
          );
        })}
      </>
    );
  }

  return (
    <AbsoluteFill style={{backgroundColor: C.bg0}}>
      <svg viewBox="0 0 1080 1920" width={width} height={height} preserveAspectRatio="xMidYMid slice" style={{position: 'absolute', inset: 0}}>
        <Defs id={id} />
        <Backdrop id={id} t={t} seed={p.shot} tint={tint} />
        {art}
      </svg>
      {p.shot === 'staged'
        ? ['Sitting 1', 'Sitting 2', 'Sitting 3'].map((s, i) => (
            <Pill key={s} text={s} x={[270, 540, 810][i]} y={775} t={t} at={0.6 + i * 0.9} u={u} color="rgba(20,14,14,0.85)" dark={false} />
          ))
        : null}
      {(p.chips ?? []).map((c, i) => {
        const pos = [[250, 330], [830, 330], [250, 880], [830, 880]][i % 4];
        return <Pill key={i} text={c.text} x={pos[0]} y={pos[1]} t={t} at={c.at_s} u={u} />;
      })}
      {p.big ? (
        <div
          style={{
            position: 'absolute', left: 0, right: 0, top: p.shot === 'staged' ? 300 * u : 560 * u, textAlign: 'center', fontFamily: FONT, fontWeight: 900,
            fontSize: (p.shot === 'staged' ? 88 : 120) * u, color: C.arrow, opacity: ramp(t, p.big_at_s ?? 0, (p.big_at_s ?? 0) + 0.3),
            transform: `scale(${0.8 + 0.2 * ramp(t, p.big_at_s ?? 0, (p.big_at_s ?? 0) + 0.3)})`,
            textShadow: `0 ${6 * u}px ${30 * u}px rgba(0,0,0,0.9)`, letterSpacing: -1 * u,
          }}
        >
          {p.big}
        </div>
      ) : null}
      {p.badge ? <Pill text={p.badge} x={540} y={868} t={t} at={p.badge_at_s ?? 0} u={u} color="#7BE38B" /> : null}
      {p.shot === 'intro' && p.name ? (
        <div
          style={{
            position: 'absolute', left: 60 * u, top: 300 * u, opacity: ramp(t, 0.2, 0.6), transform: `translateX(${(1 - ramp(t, 0.2, 0.6)) * -80 * u}px)`,
            background: 'rgba(18,13,14,0.82)', borderLeft: `${12 * u}px solid ${C.arrow}`, padding: `${20 * u}px ${34 * u}px`, fontFamily: FONT,
          }}
        >
          <div style={{color: C.white, fontWeight: 800, fontSize: 52 * u}}>{p.name}</div>
          {p.role ? <div style={{color: '#E9C9A8', fontWeight: 600, fontSize: 38 * u, marginTop: 4 * u}}>{p.role}</div> : null}
        </div>
      ) : null}
      <div style={{opacity: p.card_at_s !== undefined ? 1 - ramp(t, p.card_at_s, p.card_at_s + 0.3) : 1}}>
        <Headline text={p.headline} at={H} t={t} u={u} />
      </div>
      {p.sub ? (
        <div
          style={{
            position: 'absolute', left: 80 * u, right: 80 * u, top: 1170 * u, textAlign: 'center', fontFamily: FONT, fontWeight: 700,
            fontSize: 44 * u, color: '#F3DCC2', opacity: ramp(t, p.sub_at_s ?? H + 0.4, (p.sub_at_s ?? H + 0.4) + 0.3),
            textShadow: `0 ${4 * u}px ${18 * u}px rgba(0,0,0,0.9)`,
          }}
        >
          {p.sub}
        </div>
      ) : null}
      {p.shot === 'end' && p.card_at_s !== undefined ? (
        <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: ramp(t, p.card_at_s, p.card_at_s + 0.4)}}>
          <AbsoluteFill style={{background: 'rgba(16,11,12,0.78)'}} />
          <div style={{textAlign: 'center', fontFamily: FONT, transform: `translateY(${-160 * u}px)`}}>
            <div style={{color: C.arrow, fontWeight: 900, fontSize: 84 * u, lineHeight: 1.05, letterSpacing: -1 * u, whiteSpace: 'pre-line'}}>Consult your{'\n'}urologist</div>
            <div style={{width: 160 * u, height: 8 * u, background: C.arrow, margin: `${36 * u}px auto`, borderRadius: 8 * u}} />
            <div style={{color: C.white, fontWeight: 800, fontSize: 60 * u}}>{p.name}</div>
            <div style={{color: '#E9C9A8', fontWeight: 600, fontSize: 44 * u, marginTop: 10 * u}}>{p.role}</div>
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
