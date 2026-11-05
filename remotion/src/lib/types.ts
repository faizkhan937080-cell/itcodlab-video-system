export type TransitionDef = {
  type?: 'cut' | 'fade' | 'slide' | 'zoom';
  duration_s?: number;
};

export type SceneDef = {
  id: string;
  duration_s: number;
  template: 'title' | 'kinetic_text' | 'banner' | 'image' | 'lower_third';
  props?: Record<string, any>;
  transition_in?: TransitionDef;
};

export type Plan = {
  title: string;
  fps: number;
  orientation: 'portrait' | 'landscape';
  width: number;
  height: number;
  brand?: {colors?: Record<string, string>; font?: string};
  grain?: boolean;
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
