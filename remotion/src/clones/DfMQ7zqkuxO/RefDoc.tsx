import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {DocIcon, SoftShadow} from './parts';
import {F, K, unit} from './theme';

type Line = {text: string; at_s?: number};

/** brand-kit.md card (87.4-92.0 s): white rounded card, mono file name + "updated after every video" at right,
 * mono key lines, grey caps section label, "+ ..." lines typed in one by one. split = top half; full = page centre. */
export const RefDoc: React.FC<{file: string; note?: string; lines: Line[]; section?: string; adds?: Line[]; layout?: 'split' | 'full'; plate?: string}> = ({file, note, lines, section, adds = [], layout = 'split', plate}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  const box = layout === 'split' ? {left: 0.035 * width, top: 0.045 * height, width: 0.93 * width, height: 0.4 * height} : {left: 0.08 * width, top: 0.3 * height, width: 0.84 * width, height: 0.4 * height};
  return (
    <>
      <Page mode={layout} plate={plate} />
      <div style={{position: 'absolute', ...box}}>
        <SoftShadow r={24 * u} u={u} />
        <div style={{position: 'absolute', inset: 0, borderRadius: 24 * u, background: '#FFFFFF', border: `${1.5 * u}px solid ${K.cardLine}`, padding: `${30 * u}px ${36 * u}px`, fontFamily: F.mono, color: '#3A3835'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 12 * u, fontSize: 26 * u}}>
            <DocIcon size={30 * u} color={K.grey} />
            <div style={{flex: 1}}>{file}</div>
            {note ? <div style={{fontFamily: F.ui, fontSize: 17 * u, color: K.greyLight}}>{note}</div> : null}
          </div>
          <div style={{height: 34 * u}} />
          {lines.map((l, i) => (
            <Typed key={i} l={l} size={24 * u} />
          ))}
          {section ? <div style={{fontFamily: F.ui, fontSize: 15 * u, letterSpacing: 1.4 * u, color: K.greyLight, fontWeight: 600, marginTop: 30 * u, marginBottom: 14 * u}}>{section}</div> : null}
          {adds.map((l, i) => (
            <Typed key={i} l={{...l, text: '+ ' + l.text}} size={24 * u} />
          ))}
        </div>
      </div>
    </>
  );
};

/** Line typed in character by character (~45 chars/s) from at_s; before that it is not there. */
const Typed: React.FC<{l: Line; size: number}> = ({l, size}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const at = (l.at_s ?? 0) * fps;
  const n = Math.floor(interpolate(frame, [at, at + (l.text.length / 45) * fps], [0, l.text.length], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  if (frame < at) return <div style={{height: size * 1.55}} />;
  return <div style={{fontSize: size, lineHeight: 1.55, whiteSpace: 'pre'}}>{l.text.slice(0, n)}</div>;
};
