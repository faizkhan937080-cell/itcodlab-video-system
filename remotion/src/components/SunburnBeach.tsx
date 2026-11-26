// SUNBURN beach scene, drawn per frame on the 216x384 art canvas: sky, spinning sun, sea, towel, boy (lying/sitting), UV beams, sunscreen, hat.
import {H, PAL, W, clamp01, ease, mix, rgb} from '../lib/pixel';
import {SunState} from '../lib/sunburnState';

type C = CanvasRenderingContext2D;
export const fr = (c: C, col: string, x: number, y: number, w: number, h: number) => { c.fillStyle = col; c.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h)); };
export const hex = (v: number[]) => `rgb(${v.map((n) => Math.round(n)).join(',')})`;
const SUN: [number, number] = [176, 52];
const Z = ['#####', '...#.', '..#..', '.#...', '#####'];
const BOLT = ['..##', '.##.', '####', '..##', '.##.', '.#..'];
export const sprite = (c: C, rows: string[], col: string, x: number, y: number) => rows.forEach((r, j) => { for (let i = 0; i < r.length; i++) if (r[i] === '#') fr(c, col, x + i, y + j, 1, 1); });

/** UV beam particles from (sx,sy) to (tx,ty); bounce = they hit and reflect up-left. */
const beams = (c: C, T: number, tx: number, ty: number, bounce: boolean, n: number) => {
  for (let i = 0; i < n; i++) {
    const q = (T * 0.8 + i / n) % 1, lat = (i - n / 2) * 4;
    const hit = bounce ? 0.55 : 1, p = Math.min(q / hit, 1);
    const x0 = SUN[0] + (tx + lat - SUN[0]) * p, y0 = SUN[1] + (ty - SUN[1]) * p;
    if (q < hit) { fr(c, '#FFF3A0', x0, y0, 2, 2); fr(c, '#F2C94C', x0 + (SUN[0] - x0) * 0.04, y0 + (SUN[1] - y0) * 0.04, 2, 2); fr(c, '#F2A33A', x0 + (SUN[0] - x0) * 0.08, y0 + (SUN[1] - y0) * 0.08, 1, 1); }
    else { const r = (q - hit) / (1 - hit); fr(c, `rgba(255,243,160,${1 - r})`, tx + lat - r * 60, ty - r * 80, 2, 2); }
  }
  if (!bounce) fr(c, '#FFF3A0', tx - 3 + Math.floor(T * 12 % 3) * 3, ty - 2, 3, 3);
};

const boy = (c: C, st: SunState, T: number, tone: string) => {
  const hair = '#4A3220', trunk = '#3F7FBF', bob = Math.round(Math.sin(T * 2));
  if (st.pose === 'lie') {
    fr(c, tone, 48, 276 + bob, 34, 10); fr(c, trunk, 82, 276 + bob, 16, 10); fr(c, tone, 98, 277, 34, 4); fr(c, tone, 98, 282, 34, 4);
    fr(c, tone, 38, 274, 10, 10); fr(c, hair, 38, 274, 10, 3); fr(c, '#222', 41, 280, 3, 1); fr(c, tone, 52, 286, 14, 3);
    for (let k = 0; k < 3; k++) { const q = (T * 0.5 + k / 3) % 1; sprite(c, Z, `rgba(255,255,255,${1 - q})`, 46 + q * 14 + k * 3, 266 - q * 26); }
  } else {
    const sx = 56, hit = st.itch ? Math.sin(T * 18) * 3 : 0;
    fr(c, tone, sx, 258, 14, 26); fr(c, trunk, sx, 276, 16, 8); fr(c, tone, sx + 14, 278, 32, 6); fr(c, tone, sx + 1, 244, 12, 12); fr(c, hair, sx + 1, 244, 12, 4); fr(c, '#222', sx + 9, 250, 2, 2);
    if (st.pain || st.itch) { fr(c, tone, sx - 5, 262 + hit, 6, 4); fr(c, tone, sx - 7, 266 + hit, 4, 6); }
    else { fr(c, tone, sx + 12, 264, 8, 4); }
    if (st.pain && Math.floor(T * 8) % 2) { sprite(c, BOLT, '#FFE46B', sx - 14, 256); sprite(c, BOLT, '#FFE46B', sx + 18, 252); fr(c, '#fff', sx + 8, 252, 3, 2); }
    if (st.itch) for (let k = 0; k < 4; k++) { const q = (T * 2 + k / 4) % 1; for (let j = 0; j < 6; j++) fr(c, '#B8E04A', sx - 14 + (j % 2) * 3 + k * 6, 270 - q * 24 - j * 2, 2, 1); }
    if (st.screen > 0.01) { // sunscreen: white patches grow, dollops fly from the tube
      const n = Math.floor(st.screen * 18);
      for (let i = 0; i < n; i++) fr(c, '#F2F2F2', sx + 1 + (i * 5) % 12, 260 + ((i * 7) % 24), 3, 2);
      for (let i = 0; i < Math.floor(st.screen * 8); i++) fr(c, '#F2F2F2', sx + 16 + i * 4, 279 + (i % 2), 4, 2);
      fr(c, '#2FA6C9', sx + 22, 252 - Math.round(Math.sin(T * 10)), 5, 12); fr(c, '#F2F2F2', sx + 22, 250, 5, 3);
      const q = (T * 5) % 1; if (st.screen < 0.98) fr(c, '#F2F2F2', sx + 24 - q * 12, 252 + q * 8, 3, 3);
    }
    if (st.hat > 0) { const dy = (1 - st.hat) * -40; fr(c, '#E8C45A', sx - 5, 242 + dy, 24, 3); fr(c, '#E8C45A', sx + 1, 236 + dy, 12, 7); fr(c, '#B8862E', sx + 1, 241 + dy, 12, 2); }
  }
};

export const drawBeach = (c: C, st: SunState, T: number) => {
  const z = st.zoom, k = (z - 1) / 7;
  c.setTransform(z, 0, 0, z, 66 - 66 * z + (108 - 66) * k, 281 - 281 * z + (192 - 281) * k);
  ['#6FB7D6', '#7EC8DC', '#8DD2E2', '#A0DBE8', '#B6E4EE', '#CBEBF1'].forEach((col, i) => fr(c, col, 0, i * 34, W, 34));
  const [sx, sy] = SUN, pulse = Math.round(Math.sin(T * 3));
  fr(c, 'rgba(255,230,120,0.25)', sx - 26 - pulse, sy - 26 - pulse, 52 + 2 * pulse, 52 + 2 * pulse);
  for (let dy = -18; dy <= 18; dy++) { const hw = Math.floor(Math.sqrt(18 * 18 - dy * dy)); fr(c, '#FFE46B', sx - hw, sy + dy, hw * 2, 1); fr(c, '#F2A33A', sx - hw, sy + dy, 2, 1); }
  for (let i = 0; i < 12; i++) { const a = (i * 30 + T * 24) * Math.PI / 180; for (let r = 23; r < 31; r += 3) fr(c, '#FFE46B', sx + Math.cos(a) * r, sy + Math.sin(a) * r, 3, 3); }
  if (st.mode === 'beach' && st.pose === 'lie' && st.hook >= 0) fr(c, '#fff', sx - 4, sy - 4, 2, 2);
  fr(c, '#3C8FB5', 0, 200, W, 50);
  for (let x = 0; x < W; x += 9) fr(c, '#CFEAF2', (x + T * 14 + (x % 3) * 5) % W, 206 + (x % 4) * 10, 5, 1);
  fr(c, '#E8C98A', 0, 250, W, H - 250); for (let x = 0; x < W; x += 7) fr(c, '#C9A96A', x, 256 + (x * 3) % 90, 2, 1);
  for (let x = 22; x < 178; x += 8) fr(c, (x / 8) % 2 ? '#F2F2F2' : '#D8323C', x, 286, 8, 18);
  const tone = hex(mix(rgb('#E5B88A'), rgb('#D8323C'), st.red * 0.7));
  boy(c, st, T, tone);
  if (st.beachRays === 'hit') beams(c, T, 66, 274, false, 9);
  if (st.beachRays === 'bounce-hat') beams(c, T, 63, 238, true, 9);
  if (st.beachRays === 'bounce-body') beams(c, T, 66, 262, true, 7);
  c.setTransform(1, 0, 0, 1, 0, 0);
};
export {PAL, clamp01, ease};
