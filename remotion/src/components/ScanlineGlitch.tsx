// CRT overlay: faint scanlines always, and on trigger times (0.3 s) real horizontal band displacement + RGB split of the children.
import React from 'react';
import {AbsoluteFill, random} from 'remotion';

export type GlitchHit = {t: number; dur: number};
const BANDS = 5;
export const ScanlineGlitch: React.FC<{T: number; fps: number; hits: GlitchHit[]; frame: number; children: React.ReactNode}> = ({T, fps, hits, frame, children}) => {
  const hit = hits.find((h) => T >= h.t && T < h.t + h.dur);
  const lines = <AbsoluteFill style={{pointerEvents: 'none', background: `repeating-linear-gradient(0deg, rgba(0,0,0,${hit ? 0.28 : 0.1}) 0 2px, rgba(0,0,0,0) 2px 5px)`}} />;
  if (!hit) return <AbsoluteFill>{children}{lines}</AbsoluteFill>;
  const k = Math.floor((T - hit.t) * fps); // glitch frame index
  const bands = Array.from({length: BANDS}, (_, i) => {
    const y = Math.floor(random(`gy${frame}-${i}`) * 1800), h = 30 + Math.floor(random(`gh${frame}-${i}`) * 110);
    const dx = (random(`gx${frame}-${i}`) - 0.5) * 160;
    return {y, h, dx};
  });
  return (
    <AbsoluteFill>
      {children}
      {bands.map((b, i) => (
        <AbsoluteFill key={i} style={{clipPath: `inset(${b.y}px 0 ${Math.max(0, 1920 - b.y - b.h)}px 0)`, transform: `translateX(${b.dx}px)`}}>{children}</AbsoluteFill>
      ))}
      {bands.slice(0, 2).map((b, i) => (
        <div key={`r${i}`} style={{position: 'absolute', left: 0, right: 0, top: b.y + 4, height: 6, background: i ? 'rgba(0,255,255,0.35)' : 'rgba(255,0,60,0.4)', mixBlendMode: 'screen', transform: `translateX(${(i ? -1 : 1) * (8 + k * 3)}px)`}} />
      ))}
      {lines}
    </AbsoluteFill>
  );
};
