// Meme beats recreated in Remotion (original art, no copied clips): quick cutaway/overlay formats seen on Reels and Shorts.
// BRUH slam, panic shake text, WRONG stamp, AURA points, siren flash. Each one lives dur_s seconds from at_s.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FONT, ramp} from './MedScene';

export type Meme = {kind: 'bruh' | 'panic' | 'wrong' | 'aura' | 'siren'; at_s: number; dur_s?: number; text?: string; sub?: string};

const slam = (q: number) => (q < 0.12 ? 1.9 - 0.9 * (q / 0.12) : 1 + 0.04 * Math.sin(q * 20)); // punch-in then settle
const big = (u: number, size: number, color: string, t: string) => ({
  fontFamily: FONT, fontWeight: 900 as const, fontSize: size * u, color, textAlign: 'center' as const, lineHeight: 1.0, letterSpacing: -2 * u,
  textShadow: `0 ${6 * u}px 0 #000, 0 0 ${28 * u}px rgba(0,0,0,0.8)`, WebkitTextStroke: `${6 * u}px #000`, paintOrder: 'stroke fill' as const,
});

/** Returns the screen-shake offset (px in design units) so the caller can shake the whole frame during a panic meme. */
export const shakeAt = (memes: Meme[] | undefined, t: number): {x: number; y: number} => {
  for (const m of memes ?? []) {
    if (m.kind === 'panic' && t >= m.at_s && t <= m.at_s + (m.dur_s ?? 1.2)) return {x: Math.sin(t * 90) * 14, y: Math.cos(t * 77) * 11};
  }
  return {x: 0, y: 0};
};

export const MemeLayer: React.FC<{memes?: Meme[]; t: number; u: number}> = ({memes, t, u}) => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    {(memes ?? []).map((m, i) => {
      const dur = m.dur_s ?? 1.1, q = (t - m.at_s) / dur;
      if (q < 0 || q > 1) return null;
      const fade = q > 0.82 ? 1 - (q - 0.82) / 0.18 : 1;
      const s = slam(q);
      if (m.kind === 'bruh') {
        return (
          <AbsoluteFill key={i} style={{opacity: fade}}>
            <AbsoluteFill style={{background: 'rgba(0,0,0,0.55)'}} />
            <div style={{position: 'absolute', left: 0, right: 0, top: 640 * u, ...big(u, 230, '#FFFFFF', ''), transform: `scale(${s}) rotate(-4deg)`}}>{m.text ?? 'BRUH.'}</div>
            <div style={{position: 'absolute', left: 0, right: 0, top: 930 * u, ...big(u, 66, '#FFE066', ''), transform: `scale(${slam(Math.min(1, q * 1.4))})`}}>{m.sub ?? '(aag toh lagi hi nahi)'}</div>
          </AbsoluteFill>
        );
      }
      if (m.kind === 'panic') {
        const flash = 0.25 + 0.25 * Math.sin(t * 40);
        return (
          <AbsoluteFill key={i} style={{opacity: fade}}>
            <AbsoluteFill style={{background: `rgba(255,30,20,${flash})`}} />
            <div style={{position: 'absolute', left: 0, right: 0, top: 560 * u, ...big(u, 210, '#FFFFFF', ''), transform: `scale(${s}) rotate(${Math.sin(t * 60) * 3}deg)`}}>{m.text ?? 'AAG!!!'}</div>
          </AbsoluteFill>
        );
      }
      if (m.kind === 'wrong') {
        return (
          <AbsoluteFill key={i} style={{opacity: fade}}>
            <AbsoluteFill style={{background: 'rgba(0,0,0,0.5)'}} />
            <svg viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
              <g transform={`translate(540 760) scale(${s}) rotate(-8)`}>
                <circle r={250} fill="#E5282A" stroke="#fff" strokeWidth={26} />
                <path d="M -120 -120 L 120 120 M 120 -120 L -120 120" stroke="#fff" strokeWidth={60} strokeLinecap="round" />
              </g>
            </svg>
            <div style={{position: 'absolute', left: 0, right: 0, top: 1060 * u, ...big(u, 150, '#FFFFFF', ''), transform: `scale(${slam(Math.min(1, q * 1.5))})`}}>{m.text ?? 'GALAT!'}</div>
          </AbsoluteFill>
        );
      }
      if (m.kind === 'aura') {
        return (
          <AbsoluteFill key={i} style={{opacity: fade}}>
            <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 42%, rgba(255,215,90,0.55), rgba(0,0,0,0.55) 70%)'}} />
            <div style={{position: 'absolute', left: 0, right: 0, top: 600 * u, ...big(u, 190, '#FFE066', ''), transform: `scale(${s})`}}>{m.text ?? 'AURA +1000'}</div>
            <div style={{position: 'absolute', left: 0, right: 0, top: 880 * u, ...big(u, 66, '#FFFFFF', '')}}>{m.sub ?? 'sahi jawab'}</div>
          </AbsoluteFill>
        );
      }
      const a = Math.floor(t * 8) % 2;
      return <AbsoluteFill key={i} style={{background: a ? 'rgba(255,30,20,0.35)' : 'rgba(40,90,255,0.3)', opacity: fade}} />;
    })}
  </AbsoluteFill>
);
export {ramp};
