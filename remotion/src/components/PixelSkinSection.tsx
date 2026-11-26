// Side cross-section of skin, drawn pixel by pixel on a 216x384 canvas every frame, shown pixelated at 5x. Layers per style card.
import React, {useLayoutEffect, useRef} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {H, PAL, RGB, S, W, mix, rgb} from '../lib/pixel';
import {CX, POOL_Y, SURF, SkinState} from '../lib/eightbitState';

const C = {cream: rgb(PAL.cream), brick: rgb(PAL.brick), pink: rgb(PAL.pink), dark: rgb(PAL.dark), red: rgb(PAL.red), vessel: rgb(PAL.vessel), bg: rgb(PAL.bg)};
const CAPS = [48, 66, 84, 102, 120, 138, 156, 174];
const PAP = (x: number) => SURF + 16 + Math.round(3 * Math.sin(x * 0.18));

/** Colour of one skin pixel before deformation (x, y in art px). */
export const material = (x: number, y: number, s: SkinState, f: number): RGB => {
  if (y < SURF) return C.bg;
  const pb = PAP(x);
  let c: RGB;
  if (y < pb) {
    const row = Math.floor((y - SURF) / 4), off = (row % 2) * 4;
    c = (y - SURF) % 4 === 3 || (x + off) % 8 === 7 ? C.brick : C.cream;
  } else if (y < 232) {
    const wx = s.wob ? Math.round(Math.sin(f * 0.35 + y * 0.4)) : 0;
    c = (x + wx) % 8 === 3 && y % 8 === 3 ? C.dark : C.pink;
    if (CAPS.some((cx) => x === cx + Math.round(Math.sin(y * 0.09 + cx))) && y > pb + 2 && y < 226) {
      const gone = s.snapped && Math.abs(x - CX) < 48 && (y * 7 + x * 3) % 20 >= 11;
      if (!gone) c = C.red;
    }
  } else if (y < 250) c = y === 232 || y === 249 ? C.dark : C.vessel;
  else c = (y + Math.round(4 * Math.sin(x * 0.07))) % 12 === 0 ? C.dark : C.pink;
  const rx = 100 * s.pool, ry = 34 * s.pool;
  if (s.pool > 0.01 && y > pb + 3 && y < 229) {
    const d = ((x - CX) / rx) ** 2 + ((y - POOL_Y) / ry) ** 2;
    if (d < 1 - ((x + y) % 2) * 0.08) c = (d > 0.8 && (x + y) % 4 === 0) ? mix(s.poolRgb, [255, 255, 255], 0.2) : s.poolRgb;
  }
  if (s.tint > 0 && y < pb) c = mix(c, s.poolRgb, s.tint * 0.6);
  return c;
};

export const PixelSkinSection: React.FC<{state: SkinState}> = ({state}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const f = useCurrentFrame();
  useVideoConfig();
  useLayoutEffect(() => {
    const ctx = ref.current!.getContext('2d')!;
    const img = ctx.createImageData(W, H);
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const sh = state.dent * Math.exp(-(((x - CX) / 28) ** 2)) * Math.max(0, Math.min(1, 1 - (y - SURF) / 120));
        const c = material(x, y - Math.round(sh), state, f);
        const i = (y * W + x) * 4;
        img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  });
  return <canvas ref={ref} width={W} height={H} style={{position: 'absolute', left: 0, top: 0, width: W * S, height: H * S, imageRendering: 'pixelated'}} />;
};
