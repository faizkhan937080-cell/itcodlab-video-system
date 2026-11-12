import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {SoftShadow, useIn} from './parts';
import {F, K, unit} from './theme';

type Card = {img: string; idx: string; title: string; says: string; screen: string; status?: 'approve' | 'reject'; at_s?: number};

const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));

/** Storyboard browser (72.15-79.55 s, split): browser window filling the top half (top edge cropped), tab + url bar,
 * big bold title, "runtime / beats / B-rolls" line, green/red/grey pills and a big dark picture; at scroll_s the page
 * scrolls to beat cards: dark thumbnail left, mono idx line, bold title, SAYS / ON SCREEN, Approve / Reject buttons. */
export const RefCards: React.FC<{tab: string; title: string; stats: string[]; hero: string; cards: Card[]; scroll_s?: number; plate?: string}> = ({tab, title, stats, hero, cards, scroll_s = 1.0, plate}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const u = unit(width);
  const box = {left: 0.015 * width, top: 0.008 * height, width: 0.96 * width, height: 0.477 * height};
  const s = interpolate(frame, [scroll_s * fps, (scroll_s + 0.45) * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ease = 1 - Math.pow(1 - s, 3);
  const scrollPx = ease * 0.43 * height;
  return (
    <>
      <Page mode="split" plate={plate} />
      <div style={{position: 'absolute', ...box}}>
        <SoftShadow r={22 * u} u={u} />
        <div style={{position: 'absolute', inset: 0, borderRadius: 22 * u, background: K.card, border: `${2 * u}px solid ${K.cardLine}`, overflow: 'hidden', fontFamily: F.sans, color: K.ink}}>
          <div style={{height: 46 * u, background: '#ECEAE5', display: 'flex', alignItems: 'flex-end', paddingLeft: 24 * u}}>
            <div style={{background: K.card, borderRadius: `${12 * u}px ${12 * u}px 0 0`, padding: `${8 * u}px ${22 * u}px`, fontSize: 19 * u, fontFamily: F.ui}}>{tab}</div>
          </div>
          <div style={{height: 44 * u, display: 'flex', alignItems: 'center', padding: `0 ${22 * u}px`, gap: 14 * u, borderBottom: `${1.5 * u}px solid ${K.cardLine}`}}>
            <div style={{color: K.greyLight, fontSize: 22 * u}}>‹ ›</div>
            <div style={{flex: 1, background: '#ECEAE5', borderRadius: 14 * u, height: 28 * u, fontSize: 15 * u, color: K.grey, display: 'flex', alignItems: 'center', paddingLeft: 14 * u, fontFamily: F.ui}}>claude.ai/artifact/storyboard</div>
          </div>
          <div style={{position: 'absolute', left: 0, right: 0, top: 90 * u, bottom: 0, overflow: 'hidden'}}>
            <div style={{transform: `translateY(${-scrollPx}px)`, padding: `${22 * u}px ${34 * u}px`}}>
              <div style={{fontSize: 64 * u, fontWeight: 800, lineHeight: 1.05, letterSpacing: -1.2 * u}}>{title}</div>
              <div style={{display: 'flex', gap: 22 * u, fontSize: 22 * u, marginTop: 14 * u, fontFamily: F.ui}}>
                {stats.map((t) => (
                  <div key={t}>{t}</div>
                ))}
              </div>
              <div style={{display: 'flex', gap: 14 * u, marginTop: 18 * u, fontFamily: F.ui, fontSize: 18 * u}}>
                <Pill c={K.green} t="0 approved" u={u} />
                <Pill c={K.red} t="0 rejected" u={u} />
                <Pill c={K.grey} t="0 notes" u={u} />
              </div>
              <div style={{margin: `${24 * u}px auto 0`, width: 0.62 * box.width, height: 0.26 * height, borderRadius: 22 * u, overflow: 'hidden', background: K.dark}}>
                <Img src={src(hero)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
              </div>
              <div style={{height: 0.05 * height}} />
              {cards.map((c, i) => (
                <CardView key={i} c={c} u={u} w={box.width} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

const Pill: React.FC<{c: string; t: string; u: number}> = ({c, t, u}) => (
  <div style={{border: `${1.5 * u}px solid ${c}`, color: c, borderRadius: 16 * u, padding: `${4 * u}px ${14 * u}px`, background: '#FFFFFF'}}>{t}</div>
);

const CardView: React.FC<{c: Card; u: number; w: number}> = ({c, u, w}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const done = c.at_s !== undefined && frame >= c.at_s * fps;
  const k = useIn(c.at_s ?? 0);
  return (
    <div style={{display: 'flex', gap: 22 * u, background: '#FFFFFF', border: `${2 * u}px solid ${K.cardLine}`, borderRadius: 20 * u, padding: 18 * u, marginBottom: 18 * u, width: w - 68 * u}}>
      <div style={{width: 150 * u, height: 190 * u, borderRadius: 16 * u, overflow: 'hidden', background: K.dark, flex: 'none'}}>
        <Img src={src(c.img)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </div>
      <div style={{flex: 1, fontFamily: F.ui}}>
        <div style={{fontFamily: F.mono, fontSize: 15 * u, color: K.grey}}>{c.idx}</div>
        <div style={{fontFamily: F.sans, fontSize: 30 * u, fontWeight: 800, marginTop: 4 * u}}>{c.title}</div>
        <div style={{fontSize: 13 * u, letterSpacing: 1.2 * u, color: K.greyLight, marginTop: 8 * u}}>SAYS</div>
        <div style={{fontSize: 19 * u}}>{c.says}</div>
        <div style={{fontSize: 13 * u, letterSpacing: 1.2 * u, color: K.greyLight, marginTop: 6 * u}}>ON SCREEN</div>
        <div style={{fontSize: 17 * u, color: K.grey}}>{c.screen}</div>
        <div style={{display: 'flex', gap: 10 * u, marginTop: 10 * u, fontSize: 17 * u}}>
          <div style={{padding: `${6 * u}px ${16 * u}px`, borderRadius: 10 * u, border: `${1.5 * u}px solid ${K.cardLine}`, background: done && c.status === 'approve' ? K.green : '#FFFFFF', color: done && c.status === 'approve' ? '#FFFFFF' : K.ink, transform: `scale(${done && c.status === 'approve' ? 0.96 + 0.04 * k : 1})`}}>
            {done && c.status === 'approve' ? 'Approved ✓' : 'Approve'}
          </div>
          <div style={{padding: `${6 * u}px ${16 * u}px`, borderRadius: 10 * u, border: `${1.5 * u}px solid ${K.cardLine}`, background: done && c.status === 'reject' ? K.red : '#FFFFFF', color: done && c.status === 'reject' ? '#FFFFFF' : K.ink}}>
            {done && c.status === 'reject' ? 'Rejected ×' : 'Reject'}
          </div>
        </div>
      </div>
    </div>
  );
};
