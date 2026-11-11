import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {unit} from '../lib/anim';
import {C, CLEAN_FONT, Icon} from './Clean';

/**
 * "NT" look (creator neuraltech.ai, DNA reel-DfMQ7zqkuxO-b): cream page with UI-style cards on top, the talking head
 * low-key on a dark panel below (hard 50/50 split, no divider line), full-frame punch-in on the dark panel, hard cuts only.
 * No CSS blur / box-shadow (cloud renders have no GPU): glows are radial gradients, shadows are gradient strips.
 */
export const NT = {
  page: '#E9E8E0',
  card: '#F4F3EE',
  line: '#D5D3C9',
  ink: '#211E1E',
  sub: '#8C8A83',
  dark: '#171515',
};

/** Dark panel with a soft practical-light bokeh (radial gradients only). */
const Dark: React.FC<{top?: string}> = ({top = '0%'}) => (
  <div
    style={{
      position: 'absolute',
      left: 0,
      right: 0,
      bottom: 0,
      top,
      backgroundColor: NT.dark,
      backgroundImage: [
        'radial-gradient(circle at 13% 52%, rgba(255,244,225,0.95) 0, rgba(255,244,225,0.55) 2.4%, rgba(255,244,225,0) 5.2%)',
        'radial-gradient(circle at 22% 52%, rgba(150,110,70,0.30), rgba(0,0,0,0) 46%)',
        'radial-gradient(circle at 86% 26%, rgba(70,84,118,0.28), rgba(0,0,0,0) 42%)',
        'linear-gradient(#262222, #121010)',
      ].join(','),
    }}
  />
);

/** mode: split = cream top half + dark bottom half | full = cream page | punch = dark page. */
export const NtBg: React.FC<{mode?: 'split' | 'full' | 'punch'}> = ({mode = 'split'}) => (
  <AbsoluteFill style={{backgroundColor: NT.page, fontFamily: CLEAN_FONT}}>
    {mode === 'split' ? <Dark top="50%" /> : null}
    {mode === 'punch' ? <Dark /> : null}
  </AbsoluteFill>
);

type Row = {text: string; sub?: string; icon?: string; at_s?: number; hi?: boolean};

const Surface: React.FC<{u: number; style?: React.CSSProperties; children: React.ReactNode}> = ({u, style, children}) => (
  <div style={{position: 'relative', ...style}}>
    <div style={{position: 'absolute', left: 10 * u, right: 10 * u, bottom: -20 * u, height: 26 * u, background: 'linear-gradient(rgba(33,30,30,0.13), rgba(33,30,30,0))', borderRadius: 14 * u}} />
    <div style={{position: 'relative', background: `linear-gradient(${NT.card}, #EEEDE6)`, border: `${1.6 * u}px solid ${NT.line}`, borderRadius: 34 * u, padding: `${34 * u}px ${44 * u}px`}}>{children}</div>
  </div>
);

/**
 * UI card. props: layout split|full, kicker ("Step 1"), title, rows[{text, sub, icon check|cross|down|up|clock, at_s, hi}],
 * big {value, unit, at_s} (a large number line), chip (pill text). at_s = seconds after the card starts.
 * split: card sits in the top half (below the top unsafe band); full: bigger centred card with a slow push-in.
 */
export const NtCard: React.FC<Record<string, any>> = (p) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const u = unit(width, height);
  const full = p.layout === 'full';
  const inP = spring({frame, fps, config: {damping: 18, stiffness: 140, mass: 1}}); // DNA spring 18/140/1
  const rows: Row[] = p.rows ?? [];
  const push = full ? 1 + 0.045 * (frame / Math.max(1, durationInFrames)) : 1;
  const box: React.CSSProperties = full
    ? {left: 70 * u, right: 70 * u, top: 0.2 * height, bottom: 0.42 * height}
    : {left: 52 * u, right: 52 * u, top: 0.092 * height, bottom: 0.52 * height};
  const titleSize = (full ? 104 : 54) * u;
  return (
    <AbsoluteFill style={{fontFamily: CLEAN_FONT, color: NT.ink}}>
      <div
        style={{
          position: 'absolute',
          ...box,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: Math.min(1, inP * 1.5),
          transform: `translateY(${(1 - inP) * 28 * u}px) scale(${push})`,
        }}
      >
        <Surface u={u} style={{width: '100%'}}>
          <div style={{textAlign: 'center', lineHeight: 1.18}}>
            {p.kicker ? <span style={{fontSize: (full ? 52 : 40) * u, fontWeight: 500, color: NT.sub, marginRight: 16 * u}}>{p.kicker}</span> : null}
            {p.title ? <span style={{fontSize: titleSize, fontWeight: 800}}>{p.title}</span> : null}
          </div>
          {p.sub ? <div style={{textAlign: 'center', fontSize: (full ? 50 : 36) * u, fontWeight: 500, color: NT.sub, marginTop: 14 * u}}>{p.sub}</div> : null}
          {p.big ? (
            <div style={{textAlign: 'center', marginTop: 20 * u, opacity: interpolate(frame, [(p.big.at_s ?? 0) * fps, (p.big.at_s ?? 0) * fps + 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>
              <span style={{fontSize: 150 * u, fontWeight: 800, letterSpacing: -3 * u, fontFamily: `ui-monospace, "SF Mono", Menlo, monospace, ${CLEAN_FONT}`}}>{p.big.value}</span>
              {p.big.unit ? <span style={{fontSize: 56 * u, fontWeight: 700, color: NT.sub, marginLeft: 20 * u}}>{p.big.unit}</span> : null}
            </div>
          ) : null}
          {rows.length ? <div style={{height: 22 * u}} /> : null}
          {rows.map((r, i) => {
            const at = Math.round((r.at_s ?? 0) * fps);
            const s = spring({frame: frame - at, fps, config: {damping: 16, stiffness: 150, mass: 0.8}});
            const done = frame >= at + Math.round(0.45 * fps);
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 26 * u,
                  marginTop: i ? 16 * u : 0,
                  padding: `${14 * u}px ${20 * u}px`,
                  borderRadius: 22 * u,
                  background: r.hi ? 'rgba(14,107,80,0.10)' : 'rgba(255,255,255,0.55)',
                  border: `${(r.hi ? 2.6 : 1.4) * u}px solid ${r.hi ? C.green : NT.line}`,
                  // rows are on the card from the start (dim), each lights up when it is spoken: the card is never empty
                  opacity: 0.38 + 0.62 * Math.min(1, s * 1.5),
                  transform: `scale(${0.985 + 0.015 * Math.min(1, s)})`,
                }}
              >
                <Icon name={r.icon ?? 'check'} size={(full ? 76 : 62) * u} />
                <div style={{flex: 1}}>
                  <div style={{fontSize: (full ? 60 : 48) * u, fontWeight: 800, lineHeight: 1.12}}>{r.text}</div>
                  {r.sub ? <div style={{fontSize: (full ? 38 : 30) * u, fontWeight: 500, color: NT.sub, marginTop: 4 * u}}>{r.sub}</div> : null}
                </div>
                {r.icon === 'cross' ? null : (
                  <div style={{width: 44 * u, height: 44 * u, borderRadius: 10 * u, border: `${2.4 * u}px solid ${done ? C.green : NT.line}`, background: done ? C.green : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 30 * u, fontWeight: 900, flex: 'none'}}>
                    {done ? '✓' : ''}
                  </div>
                )}
              </div>
            );
          })}
          {p.chip ? (
            <div style={{display: 'flex', justifyContent: 'center', marginTop: 24 * u}}>
              <div style={{background: NT.ink, color: '#fff', borderRadius: 60 * u, padding: `${14 * u}px ${38 * u}px`, fontSize: 44 * u, fontWeight: 700}}>{p.chip}</div>
            </div>
          ) : null}
        </Surface>
      </div>
    </AbsoluteFill>
  );
};
