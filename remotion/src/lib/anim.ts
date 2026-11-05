import {Easing, interpolate, spring} from 'remotion';

/** Size unit: 1 at 1080 px on the short side, so layouts scale to 4K automatically. */
export const unit = (width: number, height: number) => Math.min(width, height) / 1080;

export const popIn = (frame: number, fps: number, delay = 0) =>
  spring({frame: frame - delay, fps, config: {damping: 14, stiffness: 120, mass: 0.7}});

export const easeOut = (frame: number, start: number, end: number, from = 0, to = 1) =>
  interpolate(frame, [start, end], [from, to], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
