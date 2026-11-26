// Shared pixel-art helpers for the 8bit_sciences style. Art grid 216x384, scale 5 -> 1080x1920. Own art, drawn by code; no stills.
import {random} from 'remotion';

export const S = 5;
export const W = 216;
export const H = 384;
export const PAL = {
  bg: '#121115', pink: '#C67579', cream: '#E5CEA9', dark: '#7A3B45', yellow: '#E8D9A0', green: '#5BA66B', sky: '#7EC8DC',
  red: '#D8323C', vessel: '#8E2433', brick: '#C9B58F', white: '#F2F2F2', grey: '#C9C9D6', nucleus: '#3A2A55', brown: '#8A6A3A', trunk: '#6B4A2B',
};
export type RGB = [number, number, number];
export const rgb = (hex: string): RGB => [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)];
export const mix = (a: RGB, b: RGB, q: number): RGB => {
  const k = Math.min(1, Math.max(0, q));
  return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k];
};
export const clamp01 = (q: number) => Math.min(1, Math.max(0, q));
export const ease = (q: number) => 1 - (1 - clamp01(q)) ** 3;
export const rnd = (seed: string) => random(seed);

export type Sprite = {rows: string[]; colors: Record<string, string>};
/** Draw a sprite (chars map to colours, '.' is clear) at integer art-pixel x,y. */
export const drawSprite = (ctx: CanvasRenderingContext2D, sp: Sprite, x: number, y: number, flip = false) => {
  sp.rows.forEach((row, j) => {
    for (let i = 0; i < row.length; i++) {
      const c = sp.colors[row[i]];
      if (!c) continue;
      ctx.fillStyle = c;
      ctx.fillRect(Math.round(x) + (flip ? row.length - 1 - i : i), Math.round(y) + j, 1, 1);
    }
  });
};
