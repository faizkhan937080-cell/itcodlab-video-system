// One timeline for the SUNBURN video: absolute time T + beats (beats-sunburn-v1.json) -> what is on screen.
import {clamp01, ease} from './pixel';

export type SBeat = {id: string; t: [number, number]; label?: string; counter?: string; sound?: string};
export const SURF = 120; // skin surface row (art px)
export const CX = 108;
const ZSTEPS = [1, 2, 3, 4, 6, 8];
const span = (bs: SBeat[], id: string): [number, number] => bs.find((b) => b.id === id)?.t ?? [1e9, 1e9];

export type SunState = {
  mode: 'beach' | 'skin'; pose: 'lie' | 'sit'; zoom: number; beachRays: 'hit' | 'bounce-body' | 'bounce-hat' | null;
  rays: number; rayDepth: number; dnaShow: boolean; crack: number; scar: boolean; alarm: boolean; widen: number; red: number; heat: number;
  rush: number; nerve: boolean; pain: boolean; immune: number; die: number; tight: number; itch: boolean; melanin: number; lift: number;
  peel: number; fall: number; fresh: number; screen: number; hat: number; label: string; labelT0: number; counter: string | null;
  icon: boolean; hook: number; callout: {x: number; y: number} | null;
};
const CALL: Record<string, [number, number]> = {
  b3: [CX, SURF], b4: [CX + 24, SURF + 30], b5: [CX + 20, 190], b7: [CX + 14, 150], b8: [40, 275], b9: [CX + 60, 262], b11: [50, 300],
  b13: [CX + 44, SURF + 52], b15: [40, SURF + 28], b16: [CX, SURF + 6], b19: [CX - 50, SURF + 41], b20: [26, SURF - 8], b22: [CX, SURF - 4],
  b23: [CX, 240], b24: [CX, SURF + 6], b25: [CX + 14, 196],
};
export const sunGlitch = (bs: SBeat[]) => [...bs.filter((b) => b.counter).map((b) => ({t: b.t[0], dur: 0.3})), {t: span(bs, 'b3')[0] + 0.55, dur: 0.3}];

export const sunAt = (T: number, bs: SBeat[]): SunState => {
  const P = (id: string) => { const [a, z] = span(bs, id); return clamp01((T - a) / (z - a)); };
  const at = (id: string) => (T >= span(bs, id)[0] ? 1 : 0);
  const inB = (id: string) => T >= span(bs, id)[0] && T < span(bs, id)[1];
  const b3 = span(bs, 'b3')[0];
  const beachIds = ['b1', 'b2', 'b12', 'b17', 'b26', 'b27'];
  const zin = T >= b3 && T < b3 + 0.6;
  const mode: SunState['mode'] = beachIds.some(inB) || zin ? 'beach' : 'skin';
  let zoom = 1;
  if (zin) zoom = ZSTEPS[Math.min(5, Math.floor(((T - b3) / 0.6) * 6))];
  for (const id of ['b12', 'b17', 'b26']) if (inB(id) && T - span(bs, id)[0] < 0.3) zoom = ZSTEPS[5 - Math.min(5, Math.floor(((T - span(bs, id)[0]) / 0.3) * 6))];
  const lab = bs.find((b) => inB(b.id));
  const cnt = bs.filter((b) => b.counter && b.t[0] <= T).pop();
  const crack = inB('b5') ? ease(P('b5') * 1.5) : T >= span(bs, 'b25')[0] ? 1 - clamp01(P('b25') * 2.5) : T > span(bs, 'b5')[1] ? 1 : 0;
  const redBase = ease(P('b9')) * (1 - 0.9 * ease(P('b24')));
  const sun = ease(P('b26'));
  return {
    mode, pose: inB('b1') || inB('b2') || zin ? 'lie' : 'sit', zoom,
    beachRays: inB('b2') ? 'hit' : inB('b27') ? 'bounce-hat' : inB('b26') && sun > 0.6 ? 'bounce-body' : null,
    rays: T >= b3 + 0.6 && T < span(bs, 'b10')[0] ? 1 : 0, rayDepth: ease(P('b4')),
    dnaShow: inB('b5') || inB('b25'), crack, scar: T >= span(bs, 'b25')[0], alarm: inB('b7'),
    widen: ease(P('b8')) * (1 - 0.7 * ease(P('b24'))), red: redBase, heat: ease(P('b9')) * (1 - ease(P('b11'))),
    rush: inB('b9') ? 1 : 0, nerve: inB('b11') || inB('b12'), pain: inB('b12'), immune: ease(P('b13')) * (1 - ease(P('b16'))),
    die: ease(P('b15')), tight: ease(P('b16')) * (1 - at('b22')), itch: inB('b17'),
    melanin: ease(P('b19')) * (1 - 0.5 * ease(P('b24'))), lift: ease(P('b20')), peel: P('b22'), fall: P('b23'), fresh: ease(P('b24')),
    screen: sun, hat: inB('b27') ? ease((T - span(bs, 'b27')[0]) / 0.5) : 0,
    label: lab ? lab.label ?? lab.counter ?? '' : '', labelT0: lab ? lab.t[0] : 0, counter: cnt?.counter ?? null, icon: !!lab?.counter,
    hook: inB('b1') ? T / span(bs, 'b1')[1] : -1, callout: lab && CALL[lab.id] && !zin ? {x: CALL[lab.id][0], y: CALL[lab.id][1]} : null,
  };
};
