import React from 'react';
import {AbsoluteFill, Freeze, useCurrentFrame, useVideoConfig} from 'remotion';
import {unit} from '../lib/anim';
import {FxDef, fxAt, noise} from '../lib/fx';

/** One colour channel of the scene: scene + colour multiply, then added (screen) onto the others. Blend modes only, no filters. */
const Channel: React.FC<{tint: string; dx: number; children: React.ReactNode}> = ({tint, dx, children}) => (
  <AbsoluteFill style={{mixBlendMode: 'screen', isolation: 'isolate'}}>
    <AbsoluteFill style={{transform: `translateX(${dx}px)`}}>{children}</AbsoluteFill>
    <AbsoluteFill style={{backgroundColor: tint, mixBlendMode: 'multiply'}} />
  </AbsoluteFill>
);

/**
 * Wraps a scene and applies meme effects at given scene times: shake, zoom_punch, flash, rgb_split, glitch, freeze.
 * With no fx it renders the children unchanged (zero cost).
 */
export const MemeFx: React.FC<{fx?: FxDef[]; children: React.ReactNode}> = ({fx, children}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  if (!fx || fx.length === 0) return <>{children}</>;
  const u = unit(width, height);
  const t = frame / fps;
  const s = fxAt(fx, t, fps);
  const body = s.freezeAt !== null ? <Freeze frame={Math.round(s.freezeAt * fps)}>{children}</Freeze> : <>{children}</>;
  const move = `translate(${s.dx * u}px, ${s.dy * u}px) rotate(${s.rot}deg) scale(${s.scale})`;
  const split = s.split * u;
  const bands = s.glitch > 0 ? 4 : 0;
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <AbsoluteFill style={{transform: move}}>
        {split > 0.5 ? (
          <AbsoluteFill style={{backgroundColor: '#000'}}>
            <Channel tint="#ff0000" dx={-split}>{body}</Channel>
            <Channel tint="#00ff00" dx={0}>{body}</Channel>
            <Channel tint="#0000ff" dx={split}>{body}</Channel>
          </AbsoluteFill>
        ) : (
          body
        )}
        {Array.from({length: bands}).map((_, i) => {
          const seed = Math.floor(t * fps) * 7 + i * 13;
          const top = noise(seed) * 85;
          const h = 4 + noise(seed + 1) * 12;
          const shift = (noise(seed + 2) - 0.5) * 2 * 90 * u * s.glitch;
          return (
            <AbsoluteFill key={i} style={{clipPath: `inset(${top}% 0 ${Math.max(0, 100 - top - h)}% 0)`, transform: `translateX(${shift}px)`}}>
              {body}
            </AbsoluteFill>
          );
        })}
      </AbsoluteFill>
      {s.flash > 0 ? <AbsoluteFill style={{backgroundColor: '#fff', opacity: s.flash}} /> : null}
    </AbsoluteFill>
  );
};
