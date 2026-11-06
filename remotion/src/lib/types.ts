import {CaptionDef, CaptionStyle} from './captions';
import {FxDef} from './fx';
import {FollowPoint, ZoomKey} from './zoom';

export type TransitionDef = {
  type?: 'cut' | 'fade' | 'slide' | 'zoom' | 'wipe' | 'slide_up' | 'flip' | 'iris' | 'clock_wipe';
  duration_s?: number;
  overlap?: boolean; // true = the previous scene stays visible underneath while this one comes in (real cross-transition, total length unchanged)
};

export type SceneDef = {
  id: string;
  duration_s: number;
  template: 'title' | 'kinetic_text' | 'banner' | 'image' | 'lower_third' | 'video'
    | 'counter' | 'bar_chart' | 'checklist' | 'split_compare' | 'quote' | 'stroke' | 'paper_cutout' | 'lottie' | 'audio_bars' | 'meme_text' | 'sticker';
  props?: Record<string, any>;
  transition_in?: TransitionDef;
  zoom?: ZoomKey[]; // punch-in / slow push keyframes on the whole scene (footage + overlays move together)
  fx?: FxDef[]; // meme effects on the whole scene: shake, zoom_punch, flash, rgb_split, glitch, freeze
  overlays?: OverlayDef[]; // graphics drawn over the scene, optionally following a tracked subject
};

export type OverlayDef = {
  template: SceneDef['template'];
  props?: Record<string, any>;
  start_s?: number; // scene time
  end_s?: number;
  box?: {x: number; y: number; w: number; h: number}; // fixed box, fractions of the frame (centre x,y)
  follow?: FollowPoint[]; // tracked box over scene time (scripts/track.py fills it from props.track_from)
};

export type AudioDef = {
  src: string;
  at_s?: number;
  trim_start_s?: number;
  duration_s?: number;
  volume?: number;
  fade_in_s?: number;
  fade_out_s?: number;
  role?: 'voice' | 'music' | 'sfx';
  duck?: {from_s: number; to_s: number; gain?: number}[]; // windows (track time) where this track is lowered under speech
};

export type Plan = {
  title: string;
  fps: number;
  orientation: 'portrait' | 'landscape';
  width: number;
  height: number;
  brand?: {colors?: Record<string, string>; font?: string};
  grain?: boolean;
  grain_src?: string; // noise tile written by scripts/fx.py when grain is true
  vignette?: number; // 0..1 edge darkening, no filters
  audio?: AudioDef[];
  captions?: CaptionDef[];
  caption_style?: CaptionStyle;
  texture?: {src: string; opacity?: number; blend?: 'multiply' | 'overlay' | 'soft-light'}; // paper / grain image over all scenes (assets/...)
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
