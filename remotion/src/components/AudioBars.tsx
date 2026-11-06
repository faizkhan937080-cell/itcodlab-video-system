import React from 'react';
import {AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import {unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** Music-reactive bars. props: src (audio file), bars (8..64), color (brand key), y (0..1 baseline), height (0..1 of frame). Plain divs, no filters. */
export const AudioBars: React.FC<{src: string; bars?: number; color?: string; y?: number; height?: number; colors: Colors}> = ({
  src,
  bars = 32,
  color = 'coral',
  y = 0.62,
  height = 0.12,
  colors,
}) => {
  const frame = useCurrentFrame();
  const {fps, width, height: h} = useVideoConfig();
  const data = useAudioData(staticFile(src));
  const u = unit(width, h);
  if (!data) return null;
  const n = Math.max(8, Math.min(64, Math.round(bars)));
  const vis = visualizeAudio({fps, frame, audioData: data, numberOfSamples: 64}).slice(0, n);
  const gap = 6 * u;
  const bw = (width * 0.8 - gap * (n - 1)) / n;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: width * 0.1, top: h * y, display: 'flex', alignItems: 'flex-end', gap, height: h * height, transform: 'translateY(-100%)'}}>
        {vis.map((v, i) => (
          <div key={i} style={{width: bw, height: Math.max(4 * u, Math.min(1, v * 6) * h * height), background: colors[color] ?? colors.coral, borderRadius: bw / 2}} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
