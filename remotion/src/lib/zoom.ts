import {Easing} from 'remotion';

export type ZoomKey = {at_s: number; scale: number; x?: number; y?: number; ease?: 'linear' | 'out' | 'in' | 'inout'};

const EASE = {
  linear: (p: number) => p,
  out: Easing.out(Easing.cubic),
  in: Easing.in(Easing.cubic),
  inout: Easing.inOut(Easing.cubic),
};

/** Zoom state at scene time t (seconds): keyframes are interpolated, the ease of the key we move TOWARDS is used. */
export const zoomAt = (keys: ZoomKey[] | undefined, t: number): {scale: number; x: number; y: number} => {
  if (!keys || keys.length === 0) return {scale: 1, x: 0.5, y: 0.5};
  const ks = [...keys].sort((a, b) => a.at_s - b.at_s);
  const st = (k: ZoomKey) => ({scale: k.scale, x: k.x ?? 0.5, y: k.y ?? 0.5});
  if (t <= ks[0].at_s) return st(ks[0]);
  for (let i = 0; i < ks.length - 1; i++) {
    const a = ks[i];
    const b = ks[i + 1];
    if (t <= b.at_s) {
      const p = EASE[b.ease ?? 'out']((t - a.at_s) / Math.max(1e-6, b.at_s - a.at_s));
      const sa = st(a);
      const sb = st(b);
      return {scale: sa.scale + (sb.scale - sa.scale) * p, x: sa.x + (sb.x - sa.x) * p, y: sa.y + (sb.y - sa.y) * p};
    }
  }
  return st(ks[ks.length - 1]);
};

export type FollowPoint = {t: number; x: number; y: number; w: number; h: number};

/** Tracked box at scene time t (linear between points, held at both ends). */
export const followAt = (pts: FollowPoint[] | undefined, t: number): FollowPoint | null => {
  if (!pts || pts.length === 0) return null;
  if (t <= pts[0].t) return pts[0];
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i];
    const b = pts[i + 1];
    if (t <= b.t) {
      const p = (t - a.t) / Math.max(1e-6, b.t - a.t);
      return {t, x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, w: a.w + (b.w - a.w) * p, h: a.h + (b.h - a.h) * p};
    }
  }
  return pts[pts.length - 1];
};

/** Crop-window centre (fraction of source width) at time t. */
export const reframeAt = (path: {t: number; x: number}[] | undefined, t: number): number => {
  if (!path || path.length === 0) return 0.5;
  if (t <= path[0].t) return path[0].x;
  for (let i = 0; i < path.length - 1; i++) {
    if (t <= path[i + 1].t) {
      const p = (t - path[i].t) / Math.max(1e-6, path[i + 1].t - path[i].t);
      return path[i].x + (path[i + 1].x - path[i].x) * p;
    }
  }
  return path[path.length - 1].x;
};
