// SUNBURN skin cells + DNA bubble: epidermis cells (dying, immune gulp, alarm rings) and the cracking DNA ladder, per frame.
import {H, W, clamp01, mix, rgb} from '../lib/pixel';
import {CX, SURF, SunState} from '../lib/sunburnState';
import {fr, hex, sprite} from './SunburnBeach';

type C = CanvasRenderingContext2D;
export const CELLY = SURF + 28, BUB: [number, number, number] = [CX, 196, 40];
const BOLT = ['..##', '.##.', '####', '..##', '.##.', '.#..'];
const ring = (c: C, cx: number, cy: number, r: number, col: string) => { for (let a = 0; a < 6.28; a += 1 / Math.max(r, 3)) fr(c, col, cx + Math.cos(a) * r, cy + Math.sin(a) * r, 2, 2); };

export const drawCells = (c: C, st: SunState, T: number) => {
  for (let i = 0; i < 9; i++) {
    const x = 14 + i * 24, dead = clamp01((st.die - i * 0.07) / 0.35), dmg = i === 4 && T > 0 ? 1 : 0;
    const flash = dead > 0 && dead < 1 && Math.floor(T * 14) % 2;
    const body = flash ? '#fff' : hex(mix(mix(rgb('#E58E92'), rgb('#D8323C'), st.red * 0.5), rgb('#6E6470'), dead));
    const w = Math.round(18 - dead * 6), h = Math.round(20 - dead * 8);
    fr(c, '#7A3B45', x - w / 2 - 1, CELLY - h / 2 - 1, w + 2, h + 2); fr(c, body, x - w / 2, CELLY - h / 2, w, h);
    if (dead < 1) fr(c, dmg && st.crack > 0 ? '#B0306A' : '#3A2A55', x - 3, CELLY - 3, 6, 6);
    if (dead >= 1) for (let k = 0; k < 4; k++) fr(c, '#3B3440', x - 5 + k * 3, CELLY + 6 + (k % 2), 2, 2);
    if (dead > 0 && dead < 1) for (let k = 0; k < 4; k++) fr(c, '#fff', x + (k - 1.5) * 8 * dead, CELLY - 10 - dead * 8 * (k % 2 + 1), 2, 2);
  }
  if (st.melanin > 0) for (let i = 0; i < 30; i++) if (i / 30 < st.melanin) fr(c, '#5A3A22', 6 + i * 7 + (i % 3), SURF + 39 + (i % 2) * 2, 3, 3);
  if (st.alarm) {
    const f = Math.floor(T * 6) % 2;
    for (let k = 0; k < 3; k++) ring(c, CX, CELLY, ((T * 40 + k * 18) % 54) + 4, f ? '#FFE46B' : '#D8323C');
    fr(c, f ? '#FFE46B' : '#D8323C', CX - 1, CELLY - 34, 3, 9); fr(c, f ? '#FFE46B' : '#D8323C', CX - 1, CELLY - 23, 3, 3);
    for (let y = CELLY + 12; y < 270; y += 6) if (((y + T * 60) % 18) < 6) fr(c, '#FFE46B', CX, y, 2, 3);
    if (f) { fr(c, '#D8323C', 0, 0, W, 3); fr(c, '#D8323C', 0, H - 3, W, 3); fr(c, '#D8323C', 0, 0, 3, H); fr(c, '#D8323C', W - 3, 0, 3, H); }
  }
  if (st.immune > 0.01) for (let i = 0; i < 4; i++) {
    const side = i % 2 ? 1 : -1, from = side < 0 ? -14 : W + 14, home = 32 + i * 50, x = from + (home - from) * st.immune + Math.sin(T * 1.7 + i) * 3;
    const y = SURF + 54 + (i % 2) * 6 + Math.sin(T * 2.1 + i * 2) * 3, gulp = Math.floor(T * 5 + i) % 2;
    fr(c, '#C9C9D6', x - 6, y - 4, 13, 9); fr(c, '#F2F2F2', x - 5, y - 5, 11, 11); fr(c, '#C9C9D6', x - 7, y - 2, 15, 5); fr(c, '#3A2A55', x - 2, y - 2, 5, 4);
    fr(c, '#8A8AA0', x - 3, y + 3, 6, gulp ? 2 : 1); if (gulp) fr(c, '#F2F2F2', x + (side < 0 ? 8 : -9), y - 8, 3, 3);
  }
  if (st.nerve) for (let i = 0; i < 3; i++) {
    const x = [50, 108, 166][i], on = Math.floor(T * 10 + i) % 2;
    for (let k = 0; k < 4; k++) fr(c, '#FFF6B0', x - 1, 380 - ((T * 150 + i * 47 + k * 70) % 260), 3, 7);
    if (on) sprite(c, BOLT, '#FFE46B', x - 2, SURF + 12);
  }
};

export const drawDna = (c: C, st: SunState, T: number) => {
  const [bx, by, br] = BUB;
  for (let dy = -br; dy <= br; dy++) { const hw = Math.floor(Math.sqrt(br * br - dy * dy)); fr(c, '#0B0A10', bx - hw, by + dy, hw * 2, 1); fr(c, '#F2F2F2', bx - hw, by + dy, 2, 1); fr(c, '#F2F2F2', bx + hw - 2, by + dy, 2, 1); }
  fr(c, '#F2F2F2', bx - 6, by - br - 1, 12, 2); fr(c, '#F2F2F2', bx - 6, by + br - 1, 12, 2);
  for (let y = by - 34; y <= by + 34; y++) {
    const s = 14 * Math.sin(y * 0.18 + T * 1.5), near = Math.abs(y - by) < 20, d = near ? st.crack * 9 * (1 - Math.abs(y - by) / 20) : 0;
    fr(c, '#4AA8E8', bx + s + d, y, 3, 1); fr(c, '#E86AA8', bx - s - d, y, 3, 1);
    if (y % 8 === 0 && !(near && st.crack > 0.5 && Math.abs(y - by) < 12)) for (let x = -s; x < s; x += 2) fr(c, y % 16 ? '#E8D9A0' : '#5BA66B', bx + x, y, 2, 1);
  }
  if (st.crack > 0) { for (let i = 0; i < 8; i++) fr(c, '#FF4040', bx - 12 + i * 3 + (i % 2) * 2, by - 8 + (i % 4) * 5, 2, 2); if (Math.floor(T * 14) % 2) sprite(c, BOLT, '#FFE46B', bx + 6, by - 12); }
  if (st.scar) { const g = Math.floor(T * 5) % 2; fr(c, g ? '#FF4040' : '#7A1F2B', bx - 6, by - 1, 12, 3); if (g) fr(c, 'rgba(255,64,64,0.35)', bx - 10, by - 5, 20, 11); }
  if (st.dnaShow && !st.scar) for (let i = 0; i < 5; i++) { const q = (T * 1.4 + i / 5) % 1; fr(c, '#FFF3A0', bx - 24 + i * 12, by - 40 + q * 36, 2, 5); }
};
