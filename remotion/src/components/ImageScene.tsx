import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {snowFall} from '@remotion/effects/snow-fall';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

/** Ken Burns zoom on an image from Drive assets/ (copied to remotion/public by the render script).
 * push = how far the slow push-in goes (ref thebrainmaze: slow, zoom in). dust = floating specks from the official
 * @remotion/effects snowFall (WebGL: plan.gl must be set, e.g. "swangle"). */
export const ImageScene: React.FC<{src: string; caption?: string; colors: Colors; push?: number; dust?: {color?: string; size?: number; speed?: number; opacity?: number; seed?: number}}> = ({src, caption, colors, push = 0.12, dust}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const u = unit(width, height);
  const {fps} = useVideoConfig();
  const scale = 1 + push * easeOut(frame, 0, durationInFrames);
  const fx = dust
    ? [snowFall({time: frame / fps, size: dust.size ?? 2.2, speed: dust.speed ?? 18, wind: 6, windVariation: 0.8, spread: 40,
        color: dust.color ?? '#E8D6BC', opacity: dust.opacity ?? 0.55, seed: dust.seed ?? 3, sceneDepth: 3000})]
    : undefined;
  return (
    <AbsoluteFill>
      <Img
        src={staticFile(src)}
        effects={fx}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}}
      />
      {caption ? (
        <div
          style={{
            position: 'absolute',
            left: 60 * u,
            right: 60 * u,
            bottom: 120 * u,
            padding: `${24 * u}px ${36 * u}px`,
            background: 'rgba(10,25,47,0.78)',
            color: colors.white,
            fontSize: 56 * u,
            fontWeight: 700,
            borderLeft: `${10 * u}px solid ${colors.coral}`,
            opacity: easeOut(frame, 10, 30),
          }}
        >
          {caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
