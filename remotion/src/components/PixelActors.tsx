// Pixel sprites that move every frame: cricket ball, blood droplets, macrophages. Hand-drawn pixel arrays (own art).
import React, {useLayoutEffect, useRef} from 'react';
import {useCurrentFrame} from 'remotion';
import {H, PAL, S, Sprite, W, clamp01, drawSprite, ease, rgb, rnd} from '../lib/pixel';
import {CX, POOL_Y, SURF, SkinState} from '../lib/eightbitState';

export const BALL: Sprite = {rows: ['..rrr..', '.rrwrr.', 'rrrwrrr', 'rrwwrrr', 'rrrwrrr', '.rrwrr.', '..rrr..'], colors: {r: '#B3202A', w: PAL.white}};
const MAC = (open: boolean): Sprite => ({rows: ['...ggggg...', '..gwwwwwg..', '.gwwwwwwwg.', 'gwwwnnnwwwg', 'gwwnnnnnwwg', 'gwwwnnnwwwg', open ? 'gwwwwoowwwg' : 'gwwwwwwwwwg', '.gwwwwwwwg.', '..gwwwwwg..', '...ggggg...'], colors: {g: PAL.grey, w: PAL.white, n: PAL.nucleus, o: '#8A8AA0'}});
export const BOY: Sprite = {rows: ['..hhhh..', '.hhhhhh.', '.hkkkkh.', '..kkkk..', '.bbbbbb.', 'bbbbbbbb', 'bbbbbbbb', '.bbbbbb.', '.pp..pp.', '.pp..pp.', '.pp..pp.', '.ss..ss.'], colors: {h: '#4A3220', k: '#E5B88A', b: '#3F7FBF', p: '#2B3A67', s: '#222'}};

const DROPS = 14;
const MACS = 4;
/** Absolute state T = seconds of the whole video, needed for the particle times. */
export const PixelActors: React.FC<{state: SkinState; T: number}> = ({state, T}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const f = useCurrentFrame();
  useLayoutEffect(() => {
    const ctx = ref.current!.getContext('2d')!;
    ctx.clearRect(0, 0, W, H);
    if (state.ballY !== null) drawSprite(ctx, BALL, CX - 3, state.ballY);
    const dc = rgb(PAL.red);
    for (let i = 0; i < DROPS; i++) {
      const dt = T - (state.dropT0 + 0.2 + i * 0.2);
      if (dt < 0 || state.dropT0 > 1e8) continue;
      const x = Math.round(CX - 34 + rnd(`dx${i}`) * 68), y0 = 168 + rnd(`dy${i}`) * 8;
      const y = y0 + 0.5 * 220 * dt * dt;
      if (y < POOL_Y - 4 && state.pool < 0.5) {
        ctx.fillStyle = `rgb(${dc.join(',')})`;
        ctx.fillRect(x, Math.round(y), 2, 3);
      }
    }
    if (state.macro) {
      const T8 = state.macroT0;
      for (let i = 0; i < MACS; i++) {
        const side = i % 2 ? 1 : -1, home = [CX - 50 + i * 32, POOL_Y - 10 + (i % 2) * 14];
        const q = Math.min(ease((T - T8 - i * 0.3) / 1.1), 1 - ease((T - (state.macroT1 - 0.9)) / 0.9));
        const x = (side < 0 ? -12 : W + 12) + (home[0] - (side < 0 ? -12 : W + 12)) * q + Math.sin(T * 1.7 + i) * 4 * q;
        const y = home[1] + Math.sin(T * 2.1 + i * 2) * 3 * q;
        drawSprite(ctx, MAC((f + i * 5) % 14 < 7), x, y);
      }
    }
  });
  return <canvas ref={ref} width={W} height={H} style={{position: 'absolute', left: 0, top: 0, width: W * S, height: H * S, imageRendering: 'pixelated'}} />;
};
export {SURF, clamp01};
