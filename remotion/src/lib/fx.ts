/** Meme / impact effects on a whole scene. Plain maths only: no blur, no boxShadow, no SVG filters (they are slow or GPU-only). */
export type FxDef = {
  type: 'shake' | 'zoom_punch' | 'flash' | 'rgb_split' | 'glitch' | 'freeze';
  start_s: number; // scene time
  dur_s?: number;
  strength?: number; // 0..2, 1 = default
};

export const FX_DEFAULT_DUR: Record<FxDef['type'], number> = {
  shake: 0.4, zoom_punch: 0.25, flash: 0.15, rgb_split: 0.35, glitch: 0.3, freeze: 0.6,
};

/** Deterministic noise 0..1 (same frame always gives the same value, so renders are repeatable). */
export const noise = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

export type FxState = {
  dx: number; dy: number; rot: number; scale: number; // shake + punch (dx,dy in unit px at 1080)
  flash: number; // white overlay 0..1
  split: number; // rgb offset in unit px
  glitch: number; // 0..1 intensity, 0 = off
  freezeAt: number | null; // scene time to hold
};

export const fxAt = (fx: FxDef[] | undefined, t: number, fps: number): FxState => {
  const s: FxState = {dx: 0, dy: 0, rot: 0, scale: 1, flash: 0, split: 0, glitch: 0, freezeAt: null};
  const f = Math.floor(t * fps);
  for (const e of fx ?? []) {
    const dur = e.dur_s ?? FX_DEFAULT_DUR[e.type];
    const k = e.strength ?? 1;
    if (t < e.start_s || t >= e.start_s + dur) continue;
    const p = (t - e.start_s) / dur; // 0..1
    const decay = 1 - p;
    if (e.type === 'shake') {
      s.dx += (noise(f * 2 + 1) - 0.5) * 2 * 28 * k * decay;
      s.dy += (noise(f * 2 + 2) - 0.5) * 2 * 28 * k * decay;
      s.rot += (noise(f * 2 + 3) - 0.5) * 2 * 1.6 * k * decay;
    } else if (e.type === 'zoom_punch') {
      s.scale *= 1 + 0.18 * k * Math.sin(Math.PI * Math.min(1, p * 1.0));
    } else if (e.type === 'flash') {
      s.flash = Math.max(s.flash, Math.min(1, 0.9 * k) * decay);
    } else if (e.type === 'rgb_split') {
      s.split = Math.max(s.split, 22 * k * decay);
    } else if (e.type === 'glitch') {
      s.glitch = Math.max(s.glitch, Math.min(2, k));
      s.split = Math.max(s.split, 14 * k);
    } else if (e.type === 'freeze') {
      s.freezeAt = e.start_s;
    }
  }
  return s;
};
