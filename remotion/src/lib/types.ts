import {CaptionDef, CaptionStyle} from './captions';

export type TransitionDef = {
  type?: 'cut' | 'fade' | 'slide' | 'zoom';
  duration_s?: number;
};

export type SceneDef = {
  id: string;
  duration_s: number;
  template: 'title' | 'kinetic_text' | 'banner' | 'image' | 'lower_third' | 'video'
    | 'counter' | 'bar_chart' | 'checklist' | 'split_compare' | 'quote' | 'stroke';
  props?: Record<string, any>;
  transition_in?: TransitionDef;
};

export type AudioDef = {
  src: string;
  at_s?: number;
  trim_start_s?: number;
  duration_s?: number;
  volume?: number;
  fade_in_s?: number;
  fade_out_s?: number;
};

export type Plan = {
  title: string;
  fps: number;
  orientation: 'portrait' | 'landscape';
  width: number;
  height: number;
  brand?: {colors?: Record<string, string>; font?: string};
  grain?: boolean;
  audio?: AudioDef[];
  captions?: CaptionDef[];
  caption_style?: CaptionStyle;
  step_fps?: number; // paper-cutout / stop-motion feel: scenes (not raw video) update only this many times per second
  scenes: SceneDef[];
};

export type Colors = Record<string, string>;

export const DEFAULT_COLORS: Colors = {
  navy: '#0A192F',
  coral: '#FF5A5F',
  white: '#FFFFFF',
  muted: '#8892B0',
};

export const sceneFrames = (durationS: number, fps: number) =>
  Math.max(1, Math.round(durationS * fps));

export const totalFrames = (plan: Plan) =>
  plan.scenes.reduce((a, s) => a + sceneFrames(s.duration_s, plan.fps), 0);
