import React from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {SoftShadow, TimedCheck} from './parts';
import {F, K, unit} from './theme';

type Row = {name: string; what: string; check_s?: number | null};

/** "The video being edited" shot (6.0-7.9 s): rounded phone card centred (x 27-73 %, y 7.3-52.7 %) whose top half is a
 * compact Step table and whose bottom half shows the talking head (the keyed clip is placed there by the video layout,
 * this card is drawn BEHIND it); timecode under it; editor timeline (ruler, V2 inserts, V1 film strip, A1 green
 * waveform, red playhead) at y 58.8-72.8 %. */
export const RefPhoneEdit: React.FC<{step: string; title: string; rows: Row[]; tc_from: number; tc_to: number; total_s?: number; plate?: string; inserts?: [number, number][]}> = ({step, title, rows, tc_from, tc_to, total_s = 60, plate, inserts = [[0.03, 0.11], [0.3, 0.38], [0.41, 0.53], [0.72, 0.8], [0.92, 0.99]]}) => {
  const frame = useCurrentFrame();
  const {width, height, fps, durationInFrames} = useVideoConfig();
  const u = unit(width);
  const p = {x: 0.27 * width, y: 0.073 * height, w: 0.46 * width, h: 0.454 * height};
  const t = tc_from + (tc_to - tc_from) * Math.min(1, frame / Math.max(1, durationInFrames - 1));
  const tc = (s: number) => {
    const f = Math.floor((s % 1) * fps);
    const ss = Math.floor(s);
    return `00:${String(Math.floor(ss / 60)).padStart(2, '0')}:${String(ss % 60).padStart(2, '0')}:${String(f).padStart(2, '0')}`;
  };
  const tl = {x: 0.075 * width, y: 0.588 * height, w: 0.85 * width, h: 0.14 * height};
  const head = (t / total_s);
  return (
    <>
      <Page mode="full" />
      <div style={{position: 'absolute', left: p.x, top: p.y, width: p.w, height: p.h}}>
        <SoftShadow r={30 * u} u={u} />
        <div style={{position: 'absolute', inset: 0, borderRadius: 30 * u, background: K.card, border: `${2 * u}px solid ${K.cardLine}`, overflow: 'hidden'}}>
          <div style={{textAlign: 'center', marginTop: 20 * u, fontFamily: F.sans, fontSize: 18 * u}}>
            <span style={{color: K.grey, marginRight: 6 * u}}>{step}</span>
            <span style={{color: K.ink, fontWeight: 700}}>{title}</span>
          </div>
          <div style={{padding: `${14 * u}px ${18 * u}px`, fontFamily: F.ui}}>
            {rows.map((r, i) => (
              <div key={i} style={{display: 'flex', alignItems: 'center', height: 42 * u, gap: 10 * u}}>
                <div style={{width: '42%', fontSize: 15 * u, fontWeight: 700, color: K.ink}}>{r.name}</div>
                <div style={{flex: 1, fontSize: 11 * u, color: K.grey}}>{r.what}</div>
                <TimedCheck at={r.check_s ?? null} size={18 * u} />
              </div>
            ))}
          </div>
          <div style={{position: 'absolute', left: 0, right: 0, top: '48%', bottom: 0, background: K.dark, overflow: 'hidden'}}>
            {plate ? <Img src={plate.startsWith('http') ? plate : staticFile(plate)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : null}
          </div>
        </div>
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0.553 * height, textAlign: 'center', fontFamily: F.mono, transform: 'translateY(-50%)'}}>
        <span style={{fontSize: 46 * u, fontWeight: 700, color: K.ink}}>{tc(t)}</span>
        <span style={{fontSize: 24 * u, color: K.greyLight}}> / {tc(total_s)}</span>
      </div>
      <div style={{position: 'absolute', left: tl.x, top: tl.y, width: tl.w, height: tl.h}}>
        <SoftShadow r={18 * u} u={u} />
        <div style={{position: 'absolute', inset: 0, borderRadius: 18 * u, background: '#FBFAF8', border: `${1.5 * u}px solid ${K.cardLine}`, overflow: 'hidden', fontFamily: F.ui}}>
          <div style={{position: 'absolute', left: 60 * u, right: 20 * u, top: 8 * u, height: 26 * u, display: 'flex', justifyContent: 'space-between', fontSize: 13 * u, color: K.grey}}>
            {['0:00', '0:10', '0:20', '0:30', '0:40', '0:50', '1:00'].map((m) => <span key={m}>{m}</span>)}
          </div>
          {[['V2', 0.3], ['V1', 0.52], ['A1', 0.76]].map(([n, y]) => (
            <div key={n as string} style={{position: 'absolute', left: 16 * u, top: (y as number) * tl.h - 10 * u, fontSize: 14 * u, color: K.grey}}>{n}</div>
          ))}
          <div style={{position: 'absolute', left: 60 * u, right: 20 * u, top: 0.22 * tl.h, height: 0.17 * tl.h}}>
            {inserts.map(([a, b], i) => (
              <div key={i} style={{position: 'absolute', left: `${a * 100}%`, width: `${(b - a) * 100}%`, height: '100%', borderRadius: 4 * u, background: '#E7E3DA', border: `${1 * u}px solid #D0CBC1`}} />
            ))}
          </div>
          <div style={{position: 'absolute', left: 60 * u, right: 20 * u, top: 0.44 * tl.h, height: 0.17 * tl.h, borderRadius: 4 * u, background: 'repeating-linear-gradient(90deg, #3B3F57 0, #3B3F57 18px, #6F6A8E 18px, #6F6A8E 22px, #C9B39A 22px, #C9B39A 26px)'}} />
          <div style={{position: 'absolute', left: 60 * u, right: 20 * u, top: 0.68 * tl.h, height: 0.17 * tl.h, borderRadius: 4 * u, background: 'repeating-linear-gradient(90deg, #8FD3A8 0, #8FD3A8 3px, #D8F0E0 3px, #D8F0E0 6px)'}} />
          <div style={{position: 'absolute', left: `calc(${60 * u}px + ${Math.min(1, head)} * (100% - ${80 * u}px))`, top: 0, bottom: 0, width: 3 * u, background: '#E5484D'}} />
        </div>
      </div>
    </>
  );
};
