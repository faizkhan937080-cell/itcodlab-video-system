// One timeline for the whole bruise video: absolute time T + beats (from beats-v1.json) -> what is on screen.
import {PAL, RGB, rgb, mix, clamp01, ease} from './pixel';

export type Beat = {id: string; t: [number, number]; label?: string; counter?: string};
export const SURF = 130; // skin surface row (art px)
export const CX = 108; // impact column
export const POOL_Y = 190;
const span = (bs: Beat[], id: string): [number, number] => bs.find((b) => b.id === id)?.t ?? [1e9, 1e9];

export type Glitch = {t: number; dur: number};
export type SkinState = {
  dent: number; snapped: boolean; pool: number; poolRgb: RGB; tint: number; wob: number;
  ballY: number | null; hit: number; dropT0: number; macro: number; macroT0: number; macroT1: number; day: string | null; icon: 'ff' | 'rewind' | null;
  callout: {text: string; x: number; y: number; t0: number} | null; hook: number; // hook: 0..1 while OUCH shows, else -1
};
const COLS: [string, string][] = [['b4', PAL.red], ['b6', '#7A1F2B'], ['b8', '#5B4A9A'], ['b10', PAL.green], ['b12', '#B8A04A']];

export const glitchTimes = (bs: Beat[]): Glitch[] => ['b1', 'b5', 'b7', 'b9', 'b11', 'b14'].filter((id) => bs.some((b) => b.id === id)).map((id) => ({t: span(bs, id)[0], dur: 0.3}));

export const stateAt = (T: number, bs: Beat[]): SkinState => {
  const b3 = span(bs, 'b3'), b4 = span(bs, 'b4'), b8 = span(bs, 'b8'), b10 = span(bs, 'b10'), b12 = span(bs, 'b12'), b6 = span(bs, 'b6');
  const tHit = b3[0] + 0.6;
  const since = T - tHit;
  const fall = clamp01((T - b3[0]) / 0.6);
  const dent = since < 0 ? 0 : since < 0.134 ? 14 * (since / 0.134) : 3 + 11 * Math.max(0, 1 - (since - 0.134) / 0.5);
  const healed = clamp01((T - b12[0]) / (b12[1] - b12[0]));
  const grow = T < b4[0] ? 0 : T < b6[0] ? 0.35 * ease((T - b4[0]) / (b4[1] - b4[0])) : T < b8[0] ? 0.35 + 0.45 * ease((T - b6[0]) / (b6[1] - b6[0])) : 0.8 + 0.2 * ease((T - b8[0]) / (b8[1] - b8[0]));
  const pool = grow * (1 - 0.95 * healed);
  let col = rgb(COLS[0][1]);
  for (let i = 0; i < COLS.length - 1; i++) {
    const a = span(bs, COLS[i][0]), z = span(bs, COLS[i + 1][0]);
    if (T >= a[0]) col = mix(rgb(COLS[i][1]), rgb(COLS[i + 1][1]), (T - a[0]) / Math.max(0.01, z[0] - a[0]));
  }
  if (T >= span(bs, 'b12')[0]) col = rgb(COLS[4][1]);
  const tint = T < b6[0] ? 0 : 0.55 * clamp01((T - b6[0]) / 0.8) * (1 - healed);
  const cnt = bs.filter((b) => b.counter && b.t[0] <= T).pop();
  const b1 = span(bs, 'b1');
  const icon: SkinState['icon'] = T >= b1[0] && T < b1[1] ? 'rewind' : cnt ? 'ff' : null;
  const lab = bs.filter((b) => b.label && !['OUCH', 'HEALED'].includes(b.label) && T >= b.t[0] + 0.3 && T < b.t[1]).pop();
  const pos: Record<string, [number, number]> = {CAPILLARY: [CX - 20, 175], BLOOD: [CX + 10, POOL_Y], MACROPHAGE: [CX + 30, POOL_Y - 6], BILIVERDIN: [CX - 20, POOL_Y], BILIRUBIN: [CX + 5, POOL_Y]};
  const p = lab ? pos[lab.label as string] ?? [CX, POOL_Y] : [0, 0];
  const mAct = T >= b8[0] && T < b10[1];
  return {
    dent: dent * (since > 0 ? 1 : 0), snapped: since >= 0, pool, poolRgb: col, tint, wob: T < b3[0] ? 1 : 0,
    ballY: T < b3[0] || since > 0.7 ? null : since < 0 ? -10 + fall ** 2 * (SURF - 7) : SURF - 7 - 34 * Math.sin(Math.PI * (since / 0.7)),
    hit: since, dropT0: b4[0], macro: mAct ? 1 : 0, macroT0: b8[0], macroT1: b10[1], day: cnt?.counter ?? null, icon,
    callout: lab ? {text: lab.label as string, x: p[0], y: p[1], t0: lab.t[0] + 0.3} : null,
    hook: T >= 0.5 && T < 0.5 + 1.3 ? (T - 0.5) / 1.3 : -1,
  };
};
