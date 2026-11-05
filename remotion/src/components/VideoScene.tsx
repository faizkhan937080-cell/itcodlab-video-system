import React from 'react';
import {AbsoluteFill, OffthreadVideo, staticFile, useVideoConfig} from 'remotion';

/**
 * Raw footage scene. The clip is drawn at the composition size, which the render script sets to the clip's own
 * resolution (4K in -> 4K out). OffthreadVideo extracts exact frames, so no quality loss.
 * props: src (Drive assets/ or input/ path), trim_start_s, trim_end_s, fit ('cover' | 'contain'), muted, volume.
 */
export const VideoScene: React.FC<{
  src: string;
  trimStartS?: number;
  trimEndS?: number;
  fit?: 'cover' | 'contain';
  muted?: boolean;
  volume?: number;
}> = ({src, trimStartS, trimEndS, fit = 'cover', muted, volume = 1}) => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <OffthreadVideo
        src={staticFile(src)}
        trimBefore={trimStartS ? Math.round(trimStartS * fps) : undefined}
        trimAfter={trimEndS ? Math.round(trimEndS * fps) : undefined}
        muted={muted}
        volume={volume}
        style={{width: '100%', height: '100%', objectFit: fit}}
      />
    </AbsoluteFill>
  );
};
