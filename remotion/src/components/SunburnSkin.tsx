// SUNBURN skin cross-section, per frame: layers, UV beams, vessels (widen/rush), nerves, heat waves, dead sheet that lifts, peels and falls.
import {H, W, clamp01, mix, rgb} from '../lib/pixel';
import {CX, SURF, SunState} from '../lib/sunburnState';
import {fr, hex} from './SunburnBeach';
import {BUB, CELLY, drawCells, drawDna} from './SunburnCell';

type C = CanvasRenderingContext2D;
const VY = 275, FRESH = '#EFA3A6';

const sheet = (c: C, st: SunState, T: number) => {
  const front = st.peel * W * 1.15, fy = st.fall ** 2 * H * 1.2, fx = st.fall * 10 * Math.sin(T * 6);
  for (let x = 0; x < W; x++) {
    let lo = -st.lift * 10 * (Math.abs(x - CX) / 108) ** 1.5;
    if (x < front) lo -= Math.min(26, (front - x) * 0.5);
    const top = Math.round(SURF + lo + fy);
    if (top > H) continue;
    for (let r = 0; r < 14; r++) {
      const brick = r % 4 === 3 || (x + (Math.floor(r / 4) % 2) * 4) % 8 === 7;
      fr(c, st.tight > 0.3 && brick ? '#D9CBA9' : brick ? '#C9B58F' : hex(mix(rgb('#E5CEA9'), rgb('#F2EAD6'), st.tight)), x + fx, top + r, 1, 1);
    }
    if (st.tight > 0.4 && x % 22 === 5) for (let r = 0; r < 8; r++) fr(c, '#7A5F3A', x + (r % 3) + fx, top + 2 + r, 1, 1);
  }
};

export const drawSkin = (c: C, st: SunState, T: number) => {
  fr(c, '#121115', 0, 0, W, H);
  const pink = hex(mix(rgb('#C67579'), rgb('#E0303A'), st.red * 0.7)), epi = hex(mix(rgb('#D98A8E'), rgb('#E0303A'), st.red * 0.6));
  fr(c, pink, 0, SURF + 44, W, H); fr(c, epi, 0, SURF + 14, W, 30); fr(c, FRESH, 0, SURF, W, 14);
  fr(c, hex(mix(rgb('#C67579'), rgb('#7A3B45'), 0.5 + st.melanin * 0.4)), 0, SURF + 37, W, 7 * (0.3 + st.melanin));
  for (let y = SURF + 50; y < H; y += 8) for (let x = (y % 16) / 2; x < W; x += 8) fr(c, '#7A3B45', x, y, 1, 1);
  const th = 2 + Math.round(st.widen * 5);
  for (let i = 0; i < 6; i++) { const x = 24 + i * 34; fr(c, '#8E2433', x, SURF + 46, 1 + Math.round(st.widen * 2), VY - SURF - 46); for (let k = 0; k < 3; k++) fr(c, '#FF5A5A', x, VY - ((T * (20 + st.widen * 50) + k * 40 + i * 9) % (VY - SURF - 46)), 2, 2); }
  fr(c, '#8E2433', 0, VY - th - 1, W, th * 2 + 2); fr(c, hex(mix(rgb('#B3202A'), rgb('#FF2A2A'), st.widen)), 0, VY - th, W, th * 2);
  for (let i = 0; i < 24; i++) fr(c, '#FF8080', (i * 9 + T * (20 + 60 * st.widen + 90 * st.rush)) % W, VY - th + 1 + (i % 3) * Math.max(1, th * 0.6), 3, 2);
  if (st.nerve || st.pain || T < 1e8) for (const x of [50, 108, 166]) fr(c, '#E8D9A0', x, SURF + 20, 1, H);
  drawCells(c, st, T);
  if (st.dnaShow) { for (const s of [-1, 1]) for (let k = 0; k < 6; k++) fr(c, '#F2F2F2', CX + s * (3 + k * 5), CELLY + 12 + k * 8, 1, 2); drawDna(c, st, T); }
  sheet(c, st, T);
  if (st.heat > 0.01) for (let k = 0; k < 9; k++) for (let y = SURF - 6; y > SURF - 60; y--) if (Math.round(y + T * 30) % 8 < 5) fr(c, `rgba(255,${100 + k * 8},60,${st.heat * 0.9})`, 12 + k * 24 + 4 * Math.sin(y * 0.3 - T * 6 + k), y, 2, 1);
  if (st.tight > 0.05) for (const s of [0, 1]) { const x = s ? W - 8 - Math.round(Math.sin(T * 6) * 2) * st.tight : 8 + Math.round(Math.sin(T * 6) * 2) * st.tight; fr(c, '#fff', x, SURF - 10, 3, 3); fr(c, '#fff', x + (s ? 3 : -3), SURF - 9, 3, 1); }
  if (st.rays > 0) {
    const end = SURF + st.rayDepth * 44;
    for (let i = 0; i < 13; i++) {
      const x = 14 + i * 16, head = (T * 110 + i * 23) % (end + 10), col = head > SURF + 14 ? '#F2A33A' : '#FFF3A0';
      if (head < end) { for (let k = 0; k < 9; k++) fr(c, k < 5 ? col : '#F2C94C', x - Math.round((head - k) * 0.2), head - k, 2, 1); }
      else fr(c, '#FFE46B', x + (i % 3) - 3, end - 2, 2, 2);
    }
  }
  if (st.fresh > 0.01) for (let i = 0; i < 7; i++) { const q = (T * 2 + i * 0.37) % 1; if (q < 0.5) fr(c, '#fff', 14 + i * 30, SURF + 2 + (i % 3) * 3, 3, 1), fr(c, '#fff', 15 + i * 30, SURF + (i % 3) * 3, 1, 5); }
};
export {BUB, H, clamp01};
