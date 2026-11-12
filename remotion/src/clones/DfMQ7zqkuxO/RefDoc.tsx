import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {StepHeader} from './StepHeader';
import {DocIcon, SoftShadow} from './parts';
import {F, K, unit} from './theme';

type Line = {text: string; at_s?: number};

/** brand-kit.md card (87.4-92.0 s): white rounded card, mono file name + "updated after every video" at right,
 * mono key lines, grey caps section label, "+ ..." lines typed in one by one. split = top half; full = page centre. */
export const RefDoc: React.FC<{file: string; note?: string; lines: Line[]; section?: string; adds?: Line[]; layout?: 'split' | 'full'; plate?: string; refs?: string[]; refsLabel?: string; step?: string; title?: string}> = ({file, note, lines, section, adds = [], layout = 'split', plate, refs, refsLabel = 'References · 1 frame / sec', step, title}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  // 51.3-54.1 s: with a "References" column of stacked thumbnails at left, the card moves to x .375-.985
  const box = layout === 'split' && refs?.length ? {left: 0.375 * width, top: 0.066 * height, width: 0.61 * width, height: 0.42 * height}
    : layout === 'split' ? {left: 0.035 * width, top: 0.045 * height, width: 0.93 * width, height: 0.4 * height} : {left: 0.08 * width, top: 0.3 * height, width: 0.84 * width, height: 0.4 * height};
  return (
    <>
      <Page mode={layout} plate={plate} />
      {step && title ? <StepHeader step={step} title={title} /> : null}
      {refs?.length ? <RefsColumn refs={refs} label={refsLabel} /> : null}
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

/** Stacked reference thumbnails (51.3 s): grey label at top, 4 rounded pictures x .03-.33, y .065-.47, settle in one by one. */
const RefsColumn: React.FC<{refs: string[]; label: string}> = ({refs, label}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  const n = Math.min(4, refs.length);
  const gap = 0.012 * height;
  const h = (0.39 * height - gap * (n - 1)) / n;
  return (
    <div style={{position: 'absolute', left: 0.03 * width, top: 0.062 * height, width: 0.3 * width}}>
      <div style={{fontFamily: F.ui, fontSize: 15 * u, color: K.grey, marginBottom: 8 * u}}>{label}</div>
      {refs.slice(0, n).map((r, i) => (
        <Thumb key={i} src={r} h={h} gap={gap} i={i} u={u} />
      ))}
    </div>
  );
};

const Thumb: React.FC<{src: string; h: number; gap: number; i: number; u: number}> = ({src, h, gap, i, u}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = interpolate(frame, [i * 0.12 * fps, (i * 0.12 + 0.3) * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{height: h, marginBottom: gap, borderRadius: 14 * u, overflow: 'hidden', background: K.dark, opacity: k, transform: `translateY(${(1 - k) * 12 * u}px)`, border: `${2 * u}px solid ${K.cardLine}`}}>
      <Img src={src.startsWith('http') ? src : staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </div>
  );
};
