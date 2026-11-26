// End scenes: hard zoom-out of the healed section onto a pixel thigh (b13), then an outdoor pixel scene (b14): sky, drifting clouds, trees, boy with bat, rolling ball.
import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill} from 'remotion';
import {BOY, BALL} from './PixelActors';
import {H, PAL, S, W, clamp01, drawSprite, rgb} from '../lib/pixel';
import {PIXEL_FONT} from './DayCounter';

const fill = (c: CanvasRenderingContext2D, col: string, x: number, y: number, w: number, h: number) => { c.fillStyle = col; c.fillRect(Math.round(x), Math.round(y), w, h); };
const GROUND = 300;

const drawThigh = (c: CanvasRenderingContext2D, show: number) => {
  fill(c, PAL.bg, 0, 0, W, H);
  for (let y = 40; y < 360; y++) {
    const hw = Math.round(40 + 6 * Math.sin(((y - 40) / 320) * Math.PI));
    fill(c, PAL.cream, 108 - hw - 2, y, hw * 2 + 4, 1);
    fill(c, PAL.pink, 108 - hw, y, hw * 2, 1);
    for (let x = 108 + hw - 14; x < 108 + hw; x++) if ((x + y) % 2 === 0) fill(c, PAL.dark, x, y, 1, 1);
  }
  if (show) { c.strokeStyle = '#fff'; c.lineWidth = 1; c.strokeRect(108 - 14.5, 150.5, 29, 46); }
};
const drawOutdoor = (c: CanvasRenderingContext2D, t: number) => {
  fill(c, PAL.sky, 0, 0, W, GROUND);
  for (let i = 0; i < 3; i++) {
    const x = ((i * 90 - t * 7) % 260 + 260) % 260 - 30, y = 50 + i * 38;
    fill(c, '#fff', x, y, 36, 8); fill(c, '#fff', x + 8, y - 6, 20, 6); fill(c, '#E4F3F8', x, y + 8, 36, 2);
  }
  for (const tx of [30, 178]) {
    fill(c, PAL.trunk, tx - 3, GROUND - 52, 6, 52);
    fill(c, PAL.green, tx - 18, GROUND - 90, 36, 44); fill(c, '#3F8450', tx - 18, GROUND - 56, 36, 6); fill(c, PAL.green, tx - 10, GROUND - 100, 20, 12);
  }
  fill(c, PAL.green, 0, GROUND, W, H - GROUND); fill(c, '#3F8450', 0, GROUND, W, 3);
  for (let x = 0; x < W; x += 12) fill(c, '#3F8450', x + ((GROUND + x) % 5), GROUND + 14 + (x % 24), 4, 2);
  drawSprite(c, BOY, 78, GROUND - 12);
  const a = -1.2 + 2.6 * Math.min(1, Math.max(0, (t % 0.9) / 0.35));
  for (let k = 0; k < 14; k++) fill(c, '#C98B4A', 78 + 8 + Math.cos(a) * k, GROUND - 8 + Math.sin(a) * k, 2, 2);
  drawSprite(c, BALL, 160 - (t * 40) % 150, GROUND + 4);
};

export const PixelScene: React.FC<{t: number; zoom: React.ReactNode; healedAt: number; outdoorAt: number}> = ({t, zoom, healedAt, outdoorAt}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const out = t >= outdoorAt;
  const q = clamp01((t - healedAt) / 0.3);
  const step = Math.floor(q * 6) / 6; // hard stepped zoom-out, 6 steps in 0.3 s
  const s = 1 - (1 - 0.12) * step;
  useLayoutEffect(() => {
    const c = ref.current!.getContext('2d')!;
    if (out) drawOutdoor(c, t - outdoorAt); else drawThigh(c, q >= 1 ? 1 : 0);
  });
  return (
    <AbsoluteFill style={{background: PAL.bg}}>
      <canvas ref={ref} width={W} height={H} style={{position: 'absolute', left: 0, top: 0, width: W * S, height: H * S, imageRendering: 'pixelated'}} />
      {!out ? (
        <AbsoluteFill style={{transformOrigin: '540px 960px', transform: `translateY(${-60 * (1 - s) / 0.88}px) scale(${s})`, outline: s < 1 ? '14px solid #fff' : 'none', opacity: q >= 1 ? 0 : 1}}>{zoom}</AbsoluteFill>
      ) : null}
      {!out && t >= healedAt + 0.2 ? <div style={{position: 'absolute', left: 0, right: 0, top: 150, textAlign: 'center', fontFamily: PIXEL_FONT, fontSize: 56, color: '#fff', textShadow: '6px 6px 0 #000', opacity: Math.floor(t * 8) % 5 === 4 ? 0.2 : 1}}>HEALED</div> : null}
    </AbsoluteFill>
  );
};
export {rgb};
