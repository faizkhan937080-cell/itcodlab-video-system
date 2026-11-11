import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadDeva} from '@remotion/google-fonts/NotoSansDevanagari';
import {unit} from '../lib/anim';

/**
 * "Clean card" look (ref reel-Dfj6PH9tIBB, heysansser): near-white page with a faint dot grid and soft mint / blue-grey
 * glow, brand wordmark with a green slash on top, white info cards (thin border, soft drop edge, dark-green accent),
 * timeline rows with square markers, quote card with one green word, chip labels. Hindi falls back to Noto Sans Devanagari.
 * No CSS blur / box-shadow (cloud renders have no GPU): glows are radial gradients, shadows are gradient strips.
 */
const inter = loadInter('normal', {weights: ['500', '700', '800'], subsets: ['latin']});
const deva = loadDeva('normal', {weights: ['500', '700', '800'], subsets: ['devanagari', 'latin']});
export const CLEAN_FONT = `${inter.fontFamily}, ${deva.fontFamily}, sans-serif`;

export const C = {
  page: '#FBFCFC',
  ink: '#141716',
  sub: '#8A8F8C',
  line: '#DCE2DF',
  green: '#0E6B50',
  mint: '#2FBF8F',
  orange: '#E0704F',
  dot: '#D3D9D6',
};

const useLife = (durS?: number) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const inP = spring({frame, fps, config: {damping: 16, stiffness: 140, mass: 0.7}});
  const total = Math.round((durS ?? 9999) * fps);
  const out = durS ? interpolate(frame, [total - 8, total], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;
  return {frame, fps, inP, out};
};

/** Background page: dots + glows + brand wordmark (+ optional footer handles). Full frame, under everything. */
export const CleanBg: React.FC<{brand?: string; footer?: string[]}> = ({brand, footer}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  const g = 26 * u;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: C.page,
        backgroundImage: [
          `radial-gradient(circle at 18% 34%, rgba(150,225,190,0.30), rgba(150,225,190,0) 34%)`,
          `radial-gradient(circle at 82% 58%, rgba(180,208,222,0.34), rgba(180,208,222,0) 30%)`,
          `radial-gradient(${C.dot} ${1.3 * u}px, transparent ${1.9 * u}px)`,
        ].join(','),
        backgroundSize: `100% 100%, 100% 100%, ${g}px ${g}px`,
        fontFamily: CLEAN_FONT,
      }}
    >
      {brand ? (
        <div style={{position: 'absolute', top: 0.035 * height, width: '100%', textAlign: 'center'}}>
          <span style={{fontSize: 62 * u, fontWeight: 800, color: C.ink, letterSpacing: -1.5 * u}}>{brand}</span>
          <span
            style={{
              display: 'inline-block',
              width: 6 * u,
              height: 74 * u,
              marginLeft: 14 * u,
              verticalAlign: 'middle',
              transform: 'skewX(-18deg)',
              background: `linear-gradient(${C.mint}, ${C.green})`,
              borderRadius: 2 * u,
            }}
          />
        </div>
      ) : null}
      {footer && footer.length ? (
        // reference: handles in one centred row at about 82% of the height, small, medium weight, dark grey
        <div style={{position: 'absolute', top: 0.82 * height, transform: 'translateY(-50%)', width: '100%', textAlign: 'center', fontSize: 34 * u, fontWeight: 600, color: C.ink, letterSpacing: -0.2 * u}}>
          {footer.map((f, i) => (
            <span key={i} style={{display: 'inline-block', marginLeft: i ? 44 * u : 0}}>{f}</span>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const Icon: React.FC<{name?: string; size: number}> = ({name, size}) => {
  const s = size;
  const st = {width: s, height: s, flex: 'none' as const};
  if (name === 'check')
    return (
      <svg viewBox="0 0 24 24" style={st}><rect x="1" y="1" width="22" height="22" rx="4" fill={C.green} /><path d="M6 12.5l4 4 8-9" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
    );
  if (name === 'cross')
    return (
      <svg viewBox="0 0 24 24" style={st}><rect x="1" y="1" width="22" height="22" rx="4" fill={C.orange} /><path d="M7 7l10 10M17 7L7 17" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" /></svg>
    );
  if (name === 'down' || name === 'up')
    return (
      <svg viewBox="0 0 24 24" style={st}><circle cx="12" cy="12" r="11" fill={name === 'down' ? C.orange : C.green} /><path d={name === 'down' ? 'M12 5v13M6.5 12.5L12 18l5.5-5.5' : 'M12 19V6M6.5 11.5L12 6l5.5 5.5'} stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
    );
  if (name === 'clock')
    return (
      <svg viewBox="0 0 24 24" style={st}><circle cx="12" cy="12" r="10.5" fill="none" stroke={C.green} strokeWidth="2.4" /><path d="M12 6.5V12l3.8 2.4" stroke={C.green} strokeWidth="2.4" fill="none" strokeLinecap="round" /></svg>
    );
  // default: 8-petal burst (generic, drawn here; not a brand logo)
  return (
    <svg viewBox="0 0 24 24" style={st}>
      {Array.from({length: 8}).map((_, i) => (
        <rect key={i} x="11" y="1.5" width="2" height="9" rx="1" fill={C.orange} transform={`rotate(${i * 45} 12 12)`} />
      ))}
    </svg>
  );
};

/** White card surface with thin border + soft lower edge (gradient strip instead of box-shadow). */
const Surface: React.FC<{u: number; accent?: boolean; topBar?: boolean; style?: React.CSSProperties; children: React.ReactNode}> = ({u, accent, topBar, style, children}) => (
  <div style={{position: 'relative', ...style}}>
    <div style={{position: 'absolute', left: 6 * u, right: 6 * u, bottom: -22 * u, height: 26 * u, background: 'linear-gradient(rgba(20,30,25,0.10), rgba(20,30,25,0))', borderRadius: 8 * u}} />
    <div
      style={{
        position: 'relative',
        background: 'linear-gradient(#FFFFFF, #F4F6F5)',
        border: `${(accent ? 2.5 : 1.5) * u}px solid ${accent ? C.green : C.line}`,
        borderTop: topBar ? `${7 * u}px solid ${C.green}` : undefined,
        borderRadius: 6 * u,
        padding: `${30 * u}px ${36 * u}px`,
      }}
    >
      {children}
    </div>
  </div>
);

type Item = {title: string; sub?: string; icon?: string};

/**
 * props: kind card|row|quote|list|chip, y (centre, fraction of height, default 0.24), dur_s (for the exit fade),
 * card: icon, title, sub, accent | row: items[{title, sub, icon}], active (index, default last) |
 * quote: lines[{text, hi}], source | list: title?, items[string] (check icons, one by one) | chip: text, icon.
 */
export const CleanCard: React.FC<Record<string, any>> = (p) => {
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  const {frame, fps, inP, out} = useLife(p.dur_s);
  const y = (p.y ?? 0.24) * height;
  const enter: React.CSSProperties = {
    opacity: out * Math.min(1, inP * 1.4),
    transform: `translateY(${(1 - inP) * 40 * u}px) scale(${0.94 + 0.06 * inP})`,
  };
  const box: React.CSSProperties = {position: 'absolute', left: 0, right: 0, top: y, transform: 'translateY(-50%)', display: 'flex', justifyContent: 'center', fontFamily: CLEAN_FONT, color: C.ink};
  const kind = p.kind ?? 'card';

  if (kind === 'row') {
    const items: Item[] = p.items ?? [];
    const active = p.active ?? items.length - 1;
    const colW = (width - 140 * u) / Math.max(1, items.length);
    const lineP = interpolate(frame, [0, 0.9 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    return (
      <AbsoluteFill style={{opacity: out}}>
        <div style={{...box, flexDirection: 'column', alignItems: 'center'}}>
          <div style={{display: 'flex', gap: 0}}>
            {items.map((it, i) => {
              const d = Math.round(i * (p.stagger_s ?? 0.35) * fps);
              const pi = spring({frame: frame - d, fps, config: {damping: 15, stiffness: 140}});
              return (
                <div key={i} style={{width: colW, display: 'flex', justifyContent: 'center', opacity: Math.min(1, pi * 1.4), transform: `translateY(${(1 - pi) * 30 * u}px)`}}>
                  <Surface u={u} topBar={i === active} style={{width: colW - 36 * u}}>
                    <Icon name={it.icon} size={48 * u} />
                    <div style={{fontSize: 46 * u, fontWeight: 800, marginTop: 14 * u, lineHeight: 1.1}}>{it.title}</div>
                    {it.sub ? <div style={{fontSize: 30 * u, fontWeight: 500, color: C.sub, marginTop: 8 * u}}>{it.sub}</div> : null}
                  </Surface>
                </div>
              );
            })}
          </div>
          <div style={{position: 'relative', width: width - 140 * u, height: 26 * u, marginTop: 34 * u}}>
            <div style={{position: 'absolute', top: 12 * u, left: 0, width: `${lineP * 100}%`, height: 3 * u, background: C.ink}} />
            {items.map((_, i) => (
              <div key={i} style={{position: 'absolute', top: 2 * u, left: colW * (i + 0.5) - 12 * u, width: 24 * u, height: 24 * u, background: i === active ? C.green : C.ink, opacity: lineP > (i + 0.5) / items.length ? 1 : 0}} />
            ))}
          </div>
        </div>
      </AbsoluteFill>
    );
  }

  if (kind === 'quote') {
    const lines: {text: string; hi?: boolean}[] = p.lines ?? [];
    return (
      <AbsoluteFill>
        <div style={{...box, flexDirection: 'column', alignItems: 'flex-start', left: 70 * u, right: 70 * u, ...enter}}>
          <Surface u={u} style={{width: '100%'}}>
            <div style={{position: 'absolute', right: 34 * u, top: 4 * u, fontSize: 150 * u, fontWeight: 800, color: C.green, lineHeight: 1}}>”</div>
            {lines.map((l, i) => (
              <div key={i} style={{fontSize: 70 * u, fontWeight: 800, lineHeight: 1.18, color: l.hi ? C.green : C.ink, marginTop: i ? 4 * u : 40 * u}}>{l.text}</div>
            ))}
            <div style={{height: 30 * u}} />
          </Surface>
          {p.source ? (
            <div style={{marginTop: 26 * u, background: '#fff', border: `${1.5 * u}px solid ${C.line}`, padding: `${12 * u}px ${20 * u}px`, fontSize: 30 * u, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 14 * u}}>
              <span style={{width: 14 * u, height: 14 * u, background: C.orange, display: 'inline-block'}} />
              {p.source}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    );
  }

  if (kind === 'list') {
    const items: string[] = p.items ?? [];
    return (
      <AbsoluteFill style={{opacity: out}}>
        <div style={{...box, flexDirection: 'column', alignItems: 'stretch', left: 90 * u, right: 90 * u}}>
          {p.title ? <div style={{fontSize: 40 * u, fontWeight: 700, color: C.sub, marginBottom: 18 * u, opacity: Math.min(1, inP * 1.4)}}>{p.title}</div> : null}
          {items.map((t, i) => {
            const d = Math.round((p.stagger_s ?? 0.6) * i * fps);
            const pi = spring({frame: frame - d, fps, config: {damping: 15, stiffness: 140}});
            return (
              <div key={i} style={{marginTop: i ? 26 * u : 0, opacity: Math.min(1, pi * 1.4), transform: `translateX(${(1 - pi) * -40 * u}px)`}}>
                <Surface u={u}>
                  <div style={{display: 'flex', alignItems: 'center', gap: 24 * u}}>
                    <Icon name={p.icon ?? 'check'} size={52 * u} />
                    <div style={{fontSize: 48 * u, fontWeight: 800, lineHeight: 1.15}}>{t}</div>
                  </div>
                </Surface>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    );
  }

  if (kind === 'chip') {
    return (
      <AbsoluteFill>
        <div style={{...box, ...enter}}>
          <div style={{background: C.ink, color: '#fff', borderRadius: 999, padding: `${20 * u}px ${40 * u}px`, fontSize: 44 * u, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 16 * u}}>
            {p.icon ? <Icon name={p.icon} size={44 * u} /> : null}
            {p.text}
          </div>
        </div>
      </AbsoluteFill>
    );
  }

  // card
  return (
    <AbsoluteFill>
      <div style={{...box, ...enter}}>
        <Surface u={u} accent={p.accent} style={{minWidth: width * 0.62, maxWidth: width - 140 * u}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 30 * u}}>
            <Icon name={p.icon} size={(p.big ? 104 : 84) * u} />
            <div>
              <div style={{fontSize: (p.big ? 82 : 60) * u, fontWeight: 800, lineHeight: 1.08, letterSpacing: -0.5 * u}}>{p.title}</div>
              {p.sub ? <div style={{fontSize: 34 * u, fontWeight: 500, color: C.sub, marginTop: 10 * u}}>{p.sub}</div> : null}
            </div>
          </div>
        </Surface>
      </div>
    </AbsoluteFill>
  );
};
