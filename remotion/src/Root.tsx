import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {Main} from './Main';
import {Plan, totalFrames} from './lib/types';

const fallback: Plan = {
  title: 'preview',
  fps: 30,
  orientation: 'portrait',
  width: 1080,
  height: 1920,
  scenes: [{id: 's1', duration_s: 2, template: 'title', props: {text: 'itcodlab'}}],
};

// The render script passes the whole plan (plus width/height) as --props.
const calculateMetadata: CalculateMetadataFunction<Plan> = ({props}) => ({
  durationInFrames: Math.max(1, totalFrames(props)),
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const Root: React.FC = () => (
  <Composition
    id="Main"
    component={Main}
    durationInFrames={Math.max(1, totalFrames(fallback))}
    fps={fallback.fps}
    width={fallback.width}
    height={fallback.height}
    defaultProps={fallback}
    calculateMetadata={calculateMetadata}
  />
);
