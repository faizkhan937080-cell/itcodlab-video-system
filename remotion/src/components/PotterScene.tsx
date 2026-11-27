// Health reel in the "tilted card + marble objects" editing style: ONE continuous scene (no cuts). A new real 3D marble object
// pops in per beat on a tilted card, words reveal one by one (blur -> sharp), decor lines draw on, fixed CTA banner at the bottom.
// Everything is a function of the scene time t (deterministic). Layout numbers measured from reference DgLclCABIa3.
import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, Sequence, interpolate, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import * as THREE from 'three';
import {FONTS} from '../ext/fonts';
import {OBJ, ObjName, POSE, SoapPink, Studio, useMats} from './PotterObjects';

type W = {w: string; st: 's' | 'i' | 'b' | 'p' | 'r' | 'c'; at: number};     // serif | serif italic | bold black | bold pink | regular sans | coral
export type PotterCap = {t0: number; t1: number; lines: W[][]; y?: number};
export type PotterObj = {obj: ObjName | 'soap_pink'; t0: number; t1: number; box: {x: number; y: number; w: number; h: number}; decor: 'dots' | 'ring' | 'brackets' | 'cross' | 'frame' | 'curves' | 'none'};
export type PotterProps = {ghost: string; key_word: string; cta_big: string; caps: PotterCap[]; objs: PotterObj[]; end_s: number};

const CW = 777, CH = 1098;                 // card size, 1080x1920 frame
const INK = '#2B1018', PINK = '#CF3F82', CORAL = '#F08A5D';
const bez = Easing.bezier(0.2, 0.8, 0.2, 1);
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Fabric: React.FC<{t: number}> = ({t}) => {
  const svg = useMemo(() => {
    const s = `<svg xmlns='http://www.w3.org/2000/svg' width='540' height='960'><filter id='n' x='0' y='0'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' seed='4'/><feColorMatrix values='0 0 0 0 0.45  0 0 0 0 0.25  0 0 0 0 0.3  0 0 0 0.55 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>`;
    return `url("data:image/svg+xml;utf8,${s}")`;
  }, []);
  const dx = Math.sin(t * 0.35) * 14, dy = Math.cos(t * 0.27) * 10;
  return (
    <AbsoluteFill style={{background: '#D6B4BB'}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at ${38 + Math.sin(t * 0.3) * 6}% 30%, #E7CDD2 0%, #D2AEB6 45%, #B98F99 100%)`}} />
      <AbsoluteFill style={{background: `repeating-linear-gradient(${100 + Math.sin(t * 0.2) * 4}deg, rgba(255,255,255,0.10) 0 90px, rgba(110,60,75,0.10) 90px 190px, rgba(255,255,255,0) 190px 260px)`, transform: `translate(${dx}px, ${dy}px) scale(1.06)`, filter: 'blur(14px)'}} />
      <AbsoluteFill style={{backgroundImage: svg, backgroundSize: '1080px 1920px', opacity: 0.55, mixBlendMode: 'multiply'}} />
    </AbsoluteFill>
  );
};

const AppTile: React.FC<{t: number}> = ({t}) => (
  <div style={{position: 'absolute', left: 540 - 69, top: 118 + Math.sin(t * 1.6) * 4, width: 138, height: 138, borderRadius: 34, background: 'linear-gradient(160deg,#5A2638,#3B1523)', boxShadow: '0 14px 30px rgba(70,25,40,0.45), 0 0 0 3px rgba(255,205,215,0.55)'}}>
    <svg viewBox="0 0 138 138" width={138} height={138}>
      <path d="M20 74 H48 L58 46 L74 98 L86 62 L94 74 H118" fill="none" stroke={CORAL} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="69" cy="30" r="0" fill={CORAL} />
    </svg>
  </div>
);

const Chevron: React.FC<{x: number; y: number; rot: number; s: number}> = ({x, y, rot, s}) => (
  <div style={{position: 'absolute', left: x, top: y, width: 150 * s, height: 150 * s, transform: `rotate(${rot}deg)`, filter: 'drop-shadow(8px 10px 6px rgba(40,10,20,0.35))'}}>
    <div style={{position: 'absolute', left: 8 * s, top: 20 * s, width: 128 * s, height: 22 * s, background: INK, transform: 'rotate(28deg)', borderRadius: 3}} />
    <div style={{position: 'absolute', left: 8 * s, top: 20 * s, width: 128 * s, height: 22 * s, background: INK, transform: 'rotate(88deg)', transformOrigin: '0 50%', borderRadius: 3}} />
  </div>
);

// ---------- decor (drawn in card coordinates) ----------
const Decor: React.FC<{kind: PotterObj['decor']; cx: number; cy: number; r: number; lt: number}> = ({kind, cx, cy, r, lt}) => {
  const k = bez(Math.min(1, lt / 0.7));
  if (kind === 'none') return null;
  if (kind === 'dots') {
    const pts: React.ReactNode[] = [];
    const n = 8, sp = r * 0.3;
    for (let i = -n; i <= n; i++) for (let j = -n; j <= n; j++) {
      const d = Math.hypot(i, j) / n;
      if (d > 1) continue;
      const a = interpolate(lt, [d * 0.5, d * 0.5 + 0.35], [0, 0.65], clamp);
      pts.push(<g key={`${i}${j}`} opacity={a * (1 - d * 0.6)} transform={`translate(${cx + i * sp} ${cy + j * sp})`}><path d="M-5 0H5M0 -5V5" stroke={INK} strokeWidth={1.6} /></g>);
    }
    return <svg width={CW} height={CH} style={{position: 'absolute', left: 0, top: 0}}>{pts}</svg>;
  }
  if (kind === 'ring') {
    const rr = r * 1.05;
    return (
      <svg width={CW} height={CH} style={{position: 'absolute', left: 0, top: 0}} opacity={k}>
        <circle cx={cx} cy={cy} r={rr * (0.9 + 0.1 * k)} fill="none" stroke={INK} strokeWidth={7} strokeLinecap="round" strokeDasharray="0.1 16" transform={`rotate(${lt * 12} ${cx} ${cy})`} />
      </svg>
    );
  }
  if (kind === 'brackets') {
    const h = r * 1.0, a = 46, sw = 5;
    const s = 0.82 + 0.18 * k;
    const c = (sx: number, sy: number) => <path d={`M${sx * a} 0 H0 V${sy * a}`} transform={`translate(${cx + sx * h * s} ${cy + sy * h * s})`} fill="none" stroke={INK} strokeWidth={sw} strokeLinecap="square" />;
    return <svg width={CW} height={CH} style={{position: 'absolute', left: 0, top: 0}} opacity={k}>{c(-1, -1)}{c(1, -1)}{c(-1, 1)}{c(1, 1)}</svg>;
  }
  if (kind === 'cross') {
    const L = 900 * k;
    const vx = cx + r * 0.95, hy = cy - r * 0.8;
    return (
      <svg width={CW} height={CH} style={{position: 'absolute', left: 0, top: 0}}>
        <path d={`M${vx} ${hy - 120} V${hy - 120 + L}`} stroke={INK} strokeWidth={1.8} fill="none" />
        <path d={`M${vx - L} ${hy} H${vx + 60}`} stroke={INK} strokeWidth={1.8} fill="none" />
        <g opacity={k} transform={`translate(${vx} ${hy})`}><path d="M-22 0H22M0 -22V22" stroke={INK} strokeWidth={3} /></g>
      </svg>
    );
  }
  if (kind === 'curves') {
    const d1 = `M${cx - r * 1.6} ${cy - r * 0.9} Q${cx - r * 0.7} ${cy - r * 0.95} ${cx - r * 0.45} ${cy - r * 0.2}`;
    const d2 = `M${cx + r * 1.5} ${cy + r * 1.2} Q${cx + r * 0.7} ${cy + r * 1.0} ${cx + r * 0.4} ${cy + r * 0.3}`;
    return (
      <svg width={CW} height={CH} style={{position: 'absolute', left: 0, top: 0}}>
        <path d={d1} stroke={INK} strokeWidth={1.8} fill="none" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - k} />
        <path d={d2} stroke={INK} strokeWidth={1.8} fill="none" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - k} />
      </svg>
    );
  }
  if (kind === 'frame') {
    const s = r * 1.55;
    return (
      <>
        <div style={{position: 'absolute', left: cx - s / 2, top: cy - s / 2 + (1 - k) * 30, width: s, height: s, background: 'radial-gradient(ellipse at 40% 30%, #4a2230, #1d0b12)', opacity: k, boxShadow: '12px 18px 26px rgba(40,10,20,0.35)'}} />
        <Decor kind="curves" cx={cx} cy={cy} r={r} lt={lt} />
      </>
    );
  }
  return null;
};

// ---------- one 3D object layer ----------
const ObjLayer: React.FC<{o: PotterObj; dur: number}> = ({o, dur}) => {
  const frame = useCurrentFrame();
  const {fps, width: vw} = useVideoConfig();
  const lt = frame / fps;
  const m = useMats();
  const name = o.obj === 'soap_pink' ? 'soap' : (o.obj as ObjName);
  const C = o.obj === 'soap_pink' ? SoapPink : OBJ[name];
  const P = POSE[name];
  const inK = bez(Math.min(1, lt / 0.32));
  const outK = interpolate(lt, [dur - 0.22, dur], [0, 1], clamp);
  const blur = (1 - inK) * 16 + outK * 12;
  const op = Math.min(1, inK * 1.4) * (1 - outK);
  const b = o.box;
  const left = b.x * CW - (b.w * CW) / 2, top = b.y * CH - (b.h * CH) / 2;
  const pw = Math.round(b.w * CW), ph = Math.round(b.h * CH);
  const sc = (0.7 + 0.3 * inK) * (1 - outK * 0.1) * P.scale;
  const yaw = P.yaw + P.sway * Math.sin(lt * 1.5) + P.spin * lt;
  const cam = 5.0;
  const bob = Math.sin(lt * 2.0) * 0.04;
  return (
    <>
      <div style={{position: 'absolute', inset: 0, opacity: op}}>
        <Decor kind={o.decor} cx={b.x * CW} cy={b.y * CH} r={Math.min(pw, ph) * 0.5} lt={lt} />
      </div>
      <div style={{position: 'absolute', left, top, width: pw, height: ph, opacity: op, filter: `blur(${blur}px) drop-shadow(0px 22px 18px rgba(80,35,50,0.32))`}}>
        <ThreeCanvas dpr={vw / 1080} width={pw} height={ph} camera={{fov: 30, position: [0, 0.9, cam], near: 0.1, far: 40}} gl={{alpha: true, antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 0.85}} style={{background: 'transparent'}}
          onCreated={({camera}) => camera.lookAt(0, 0.0, 0)}>
          <Studio />
          <group position={[0, bob, 0]} rotation={[P.tilt, yaw, 0]} scale={sc}>
            <C t={lt} m={m} />
          </group>
        </ThreeCanvas>
      </div>
    </>
  );
};

// ---------- captions ----------
const wordStyle = (st: W['st'], ff: {serif: string; sans: string}): React.CSSProperties => {
  switch (st) {
    case 's': return {fontFamily: ff.serif, fontWeight: 400, fontSize: 76, color: INK, letterSpacing: -0.5};
    case 'i': return {fontFamily: ff.serif, fontStyle: 'italic', fontWeight: 400, fontSize: 76, color: INK};
    case 'b': return {fontFamily: ff.sans, fontWeight: 800, fontSize: 98, color: INK, letterSpacing: -2};
    case 'p': return {fontFamily: ff.sans, fontWeight: 700, fontSize: 124, color: PINK, letterSpacing: -3};
    case 'r': return {fontFamily: ff.sans, fontWeight: 400, fontSize: 62, color: INK, letterSpacing: -1};
    default: return {fontFamily: ff.sans, fontWeight: 800, fontSize: 98, color: CORAL};
  }
};

const Caption: React.FC<{c: PotterCap; t: number}> = ({c, t}) => {
  const ff = {serif: FONTS['Gelasio'], sans: FONTS['Poppins']};
  const out = interpolate(t, [c.t1 - 0.16, c.t1], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: (c.y ?? 0.27) * CH, transform: 'translateY(-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity: 1 - out, filter: `blur(${out * 10}px)`}}>
      {c.lines.map((ln, li) => {
        const EM: Record<string, number> = {s: 0.47, i: 0.44, b: 0.62, p: 0.6, r: 0.52, c: 0.62};
        const SZ: Record<string, number> = {s: 76, i: 76, b: 98, p: 124, r: 78, c: 98};
        const est = ln.reduce((a, w) => a + w.w.length * EM[w.st] * SZ[w.st] + 20, -20);
        const fit = Math.min(1, 700 / est);
        return (
        <div key={li} style={{display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 20, whiteSpace: 'nowrap', transform: `scale(${fit})`, transformOrigin: '50% 60%'}}>
          {ln.map((w, wi) => {
            const k = bez(Math.min(1, Math.max(0, (t - w.at) / 0.3)));
            return (
              <span key={wi} style={{...wordStyle(w.st, ff), display: 'inline-block', opacity: k, filter: `blur(${(1 - k) * 12}px)`, transform: `translateY(${(1 - k) * 16}px) scale(${0.96 + 0.04 * k})`}}>{w.w}</span>
            );
          })}
        </div>
        );
      })}
    </div>
  );
};

// ---------- banner ----------
const Banner: React.FC<{t: number; keyWord: string; big: string}> = ({t, keyWord, big}) => {
  const ff = FONTS['Poppins'];
  const bars = useMemo(() => Array.from({length: 26}).map((_, i) => ({
    y: 14 + i * 12.2, x: 40 + random(`bx${i}`) * 520, w: 40 + random(`bw${i}`) * 300, c: ['#7A3A4C', '#C0506A', '#E08A6A', '#8a5a66', '#a06070'][Math.floor(random(`bc${i}`) * 5)], o: 0.25 + random(`bo${i}`) * 0.35,
  })), []);
  const dots = useMemo(() => Array.from({length: 70}).map((_, i) => ({y: 18 + (i % 28) * 11, x: 12 + Math.floor(i / 28) * 12, c: ['#C0506A', '#E08A6A', '#9b8a90', '#7A3A4C'][Math.floor(random(`dc${i}`) * 4)]})), []);
  const scroll = (t * 6) % 12.2;
  return (
    <div style={{position: 'absolute', left: 60, top: 1328, width: 960, height: 336, borderRadius: 28, overflow: 'hidden', background: 'linear-gradient(180deg,#43202D,#33141F)', boxShadow: '0 18px 40px rgba(50,15,25,0.45), 0 0 0 2px rgba(255,205,215,0.55)'}}>
      <svg width={960} height={336} style={{position: 'absolute', left: 0, top: 0}}>
        <g transform={`translate(0 ${-scroll})`} opacity={0.9}>
          {bars.map((b, i) => <rect key={i} x={b.x} y={b.y} width={b.w} height={4} rx={2} fill={b.c} opacity={b.o} />)}
          {bars.map((b, i) => <rect key={`r${i}`} x={960 - b.x - b.w * 0.6} y={b.y + 6} width={b.w * 0.6} height={4} rx={2} fill={b.c} opacity={b.o * 0.7} />)}
        </g>
        {dots.map((d, i) => <rect key={i} x={d.x} y={d.y} width={7} height={5} fill={d.c} opacity={0.6} />)}
        <line x1={338} y1={0} x2={338} y2={336} stroke="rgba(255,255,255,0.35)" strokeWidth={1.5} />
      </svg>
      <div style={{position: 'absolute', left: 0, right: 0, top: 36, textAlign: 'center', fontFamily: ff, fontWeight: 700, fontSize: 56, color: '#fff', textShadow: '0 0 18px rgba(255,255,255,0.25), 0 3px 4px rgba(0,0,0,0.4)'}}>
        Comment <span style={{color: CORAL}}>“{keyWord}”</span> For The
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 104, textAlign: 'center', fontFamily: ff, fontWeight: 800, fontSize: 158, lineHeight: 1.0, letterSpacing: -4, color: '#fff', textShadow: '0 0 26px rgba(255,255,255,0.4), 0 6px 8px rgba(0,0,0,0.35)'}}>
        {big}
      </div>
    </div>
  );
};

export const PotterScene: React.FC<PotterProps> = ({ghost, key_word, cta_big, caps, objs}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const sc = width / 1080;
  const t = frame / fps;
  // the stage (card + banner) is a tilted plane that sways: real camera-like motion, no zoom on stills
  const rz = Math.sin(t * 0.55) * 1.1 - 0.6, ry = Math.sin(t * 0.42 + 1) * 3.2, rx = Math.sin(t * 0.37) * 1.6 + 0.5;
  const cap = caps.find((c) => t >= c.t0 && t < c.t1);
  return (
    <AbsoluteFill>
     <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920, transform: `scale(${sc})`, transformOrigin: '0 0', overflow: 'hidden'}}>
      <Fabric t={t} />
      <AppTile t={t} />
      <AbsoluteFill style={{perspective: 2000, perspectiveOrigin: '50% 45%'}}>
        <AbsoluteFill style={{transform: `rotateZ(${rz}deg) rotateY(${ry}deg) rotateX(${rx}deg) translateY(${Math.sin(t * 0.9) * 6}px)`, transformOrigin: '50% 50%'}}>
          <div style={{position: 'absolute', left: 154, top: 280, width: CW, height: CH, borderRadius: 56, overflow: 'hidden', background: '#F7EEED', boxShadow: '0 34px 70px rgba(70,30,45,0.38), 0 0 0 3px rgba(255,214,196,0.9)'}}>
            <div style={{position: 'absolute', inset: 0, background: 'repeating-linear-gradient(115deg, rgba(255,255,255,0.7) 0 26px, rgba(206,178,184,0.16) 26px 56px)', transform: `translateX(${(t * 14) % 56}px)`}} />
            <div style={{position: 'absolute', left: -20, right: -20, top: 150, textAlign: 'center', fontFamily: FONTS['Poppins'], fontWeight: 800, fontSize: 112, letterSpacing: -4, color: 'rgba(60,30,40,0.075)', whiteSpace: 'nowrap', filter: `blur(${Math.max(0, 8 - t * 20)}px)`}}>{ghost}</div>
            <Chevron x={-6} y={-6} rot={-8} s={1.1} />
            <Chevron x={CW - 120} y={CH - 150} rot={180} s={0.6} />
            {objs.map((o, i) => {
              const from = Math.round(o.t0 * fps), dur = Math.max(1, Math.round((o.t1 - o.t0) * fps));
              return (
                <Sequence key={i} from={from} durationInFrames={dur}>
                  <ObjLayer o={o} dur={o.t1 - o.t0} />
                </Sequence>
              );
            })}
            {cap ? <Caption c={cap} t={t} /> : null}
          </div>
          <Banner t={t} keyWord={key_word} big={cta_big} />
        </AbsoluteFill>
      </AbsoluteFill>
     </div>
    </AbsoluteFill>
  );
};
