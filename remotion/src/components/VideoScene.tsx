import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {reframeAt} from '../lib/zoom';

/**
 * Raw footage scene. The clip is drawn at the composition size, which the render script sets to the clip's own
 * resolution (4K in -> 4K out). OffthreadVideo extracts exact frames, so no quality loss.
 * props: src (Drive assets/ or input/ path), trim_start_s, trim_end_s, fit ('cover' | 'contain'), muted, volume,
 *        transparent (alpha WebM from background removal), reframe_path + src_aspect (auto-reframe: a 9:16 window
 *        that follows the subject inside a wider clip; set by scripts/fx.py).
 */
const fadeMask = (f: {from: number; to: number; side?: number}): React.CSSProperties => {
  const layers = [`linear-gradient(to bottom, #000 0%, #000 ${f.from * 100}%, transparent ${f.to * 100}%)`];
  if (f.side) layers.push(`linear-gradient(to right, transparent 0%, #000 ${f.side * 100}%, #000 ${(1 - f.side) * 100}%, transparent 100%)`);
  const img = layers.join(',');
  return {
    maskImage: img,
    WebkitMaskImage: img,
    maskComposite: 'intersect',
    WebkitMaskComposite: 'source-in',
  } as React.CSSProperties;
};

export const VideoScene: React.FC<{
  src: string;
  trimStartS?: number;
  trimEndS?: number;
  fit?: 'cover' | 'contain';
  muted?: boolean;
  volume?: number;
  transparent?: boolean;
  reframePath?: {t: number; x: number}[];
  srcAspect?: number;
  scale?: number; // shrink the clip, anchored at the bottom centre (keyed person over a designed page)
  offsetY?: number; // move up (negative) / down, fraction of height
  fade?: {from: number; to: number; side?: number}; // soft edge: opaque down to `from` (fraction of the clip height), gone by `to`; `side` fades the left/right edges (fraction of width)
  blend?: 'multiply'; // white parts (a white table) melt into the page behind; needs no ancestor that isolates the stacking context
}> = ({src, trimStartS, trimEndS, fit = 'cover', muted, volume = 1, transparent, reframePath, srcAspect, scale, offsetY, blend, fade}) => {
  const {fps, width, height} = useVideoConfig();
  const frame = useCurrentFrame();
  let style: React.CSSProperties = {width: '100%', height: '100%', objectFit: fit};
  if (reframePath && reframePath.length && srcAspect && srcAspect * height > width) {
    const vw = srcAspect * height;
    const cx = reframeAt(reframePath, frame / fps);
    const left = Math.min(0, Math.max(width - vw, width / 2 - cx * vw));
    style = {position: 'absolute', left, top: 0, width: vw, height};
  }
  return (
    <AbsoluteFill style={{backgroundColor: transparent ? 'transparent' : '#000'}}>
      <OffthreadVideo
        src={staticFile(src)}
        trimBefore={trimStartS ? Math.round(trimStartS * fps) : undefined}
        trimAfter={trimEndS ? Math.round(trimEndS * fps) : undefined}
        muted={muted}
        volume={volume}
        transparent={transparent}
        style={{
          ...(scale || offsetY ? {...style, transform: `translateY(${(offsetY ?? 0) * height}px) scale(${scale ?? 1})`, transformOrigin: '50% 100%'} : style),
          ...(blend ? {mixBlendMode: blend} : {}),
          ...(fade ? fadeMask(fade) : {}),
        }}
      />
    </AbsoluteFill>
  );
};
