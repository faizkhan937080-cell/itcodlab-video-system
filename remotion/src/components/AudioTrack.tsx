import React from 'react';
import {Audio, Sequence, interpolate, staticFile, useVideoConfig} from 'remotion';
import {AudioDef} from '../lib/types';

/**
 * Music / voice-over / SFX bed. `at_s` = where it starts on the timeline, `trim_start_s` = skip into the file,
 * `duration_s` = how long it plays (default: until the video ends). Fades are linear in volume.
 */
export const AudioTrack: React.FC<{track: AudioDef; totalFrames: number}> = ({track, totalFrames}) => {
  const {fps} = useVideoConfig();
  const from = Math.round((track.at_s ?? 0) * fps);
  const len = Math.max(
    1,
    track.duration_s ? Math.round(track.duration_s * fps) : totalFrames - from,
  );
  const fin = Math.round((track.fade_in_s ?? 0) * fps);
  const fout = Math.round((track.fade_out_s ?? 0) * fps);
  const base = track.volume ?? 1;
  return (
    <Sequence from={from} durationInFrames={len}>
      <Audio
        src={staticFile(track.src)}
        trimBefore={track.trim_start_s ? Math.round(track.trim_start_s * fps) : undefined}
        volume={(f) => {
          let v = base;
          if (fin > 0) v *= interpolate(f, [0, fin], [0, 1], {extrapolateRight: 'clamp'});
          if (fout > 0) v *= interpolate(f, [len - fout, len], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          for (const d of track.duck ?? []) {
            const g = d.gain ?? 0.35;
            const a = Math.round(d.from_s * fps);
            const b = Math.round(d.to_s * fps);
            const r = Math.max(1, Math.round(0.15 * fps)); // 0.15 s ramps: no pumping
            const down = interpolate(f, [a - r, a, b, b + r], [1, g, g, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            v *= down;
          }
          return v;
        }}
      />
    </Sequence>
  );
};
