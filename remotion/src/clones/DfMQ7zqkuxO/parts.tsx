import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Checkbox} from '../../ext/remocn/checkbox';
import {FLUENT} from '../../ext/fluent/icons';
import {F, K} from './theme';

/** Folder icon (Fluent, MIT) tinted like the reference's blue folders (19.0 s Finder, 55.9 s tree). */
export const Folder: React.FC<{size: number; color?: string; open?: boolean; dim?: number}> = ({size, color = '#5DAEF2', open, dim = 1}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{opacity: dim, flex: 'none'}}>
    {FLUENT[open ? 'folder_open_24_filled' : 'folder_24_filled'].map((d, i) => (
      <path key={i} d={d} fill={color} />
    ))}
  </svg>
);

export const DocIcon: React.FC<{size: number; color?: string}> = ({size, color = K.grey}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{flex: 'none'}}>
    {FLUENT.document_24_regular.map((d, i) => (
      <path key={i} d={d} fill={color} />
    ))}
  </svg>
);

/** Soft drop shadow without CSS blur (cloud renders have no GPU): stacked translucent rounded rects. */
export const SoftShadow: React.FC<{r: number; u: number}> = ({r, u}) => (
  <>
    {[22, 14, 7].map((o, i) => (
      <div key={i} style={{position: 'absolute', left: -o * u * 0.3, right: -o * u * 0.3, top: o * u * 0.5, bottom: -o * u, borderRadius: r + o * u * 0.5, background: `rgba(60,50,40,${0.035 + i * 0.012})`}} />
    ))}
  </>
);

/** remocn Checkbox driven by time: unchecked until at_s, then checks (remocn draw-on). */
export const TimedCheck: React.FC<{at: number | null; size: number}> = ({at, size}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const on = at !== null && frame >= at * fps;
  const k = at === null ? 0 : interpolate(frame, [at * fps, at * fps + 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'relative', width: size, height: size, flex: 'none', transform: `scale(${size / 24})`, transformOrigin: 'center'}}>
      <Checkbox
        state={on ? 'checked' : 'unchecked'}
        size="lg"
        primary={K.ink}
        theme={{background: '#FFFFFF', border: K.cardLine, primaryForeground: '#FFFFFF'}}
        style={{boxBackground: on ? K.ink : '#FFFFFF', boxBorderColor: on ? K.ink : K.cardLine, checkOpacity: k, checkScale: 0.6 + 0.4 * k, checkDraw: k}}
      />
    </div>
  );
};

/** Settle-in used for every element of the reference: ease-out with soft settle, ~0.4 s (editing DNA). */
export const useIn = (at = 0) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - at * fps, fps, config: {damping: 18, stiffness: 140, mass: 1}});
};

export const sans = F.sans;
