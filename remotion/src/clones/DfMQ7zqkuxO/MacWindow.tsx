import React from 'react';
import {useVideoConfig} from 'remotion';
import {SoftShadow} from './parts';
import {F, K, unit} from './theme';

/** macOS app window of the reference (Claude desktop 12.5 s, Finder 19.0 s, folder list 29.1 s).
 * box = fractions of the frame; title = breadcrumb next to the traffic lights. */
export const MacWindow: React.FC<{box: [number, number, number, number]; title?: string; sidebar?: boolean; children?: React.ReactNode}> = ({box, title, sidebar, children}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  const [x0, y0, x1, y1] = box;
  const r = 26 * u;
  return (
    <div style={{position: 'absolute', left: x0 * width, top: y0 * height, width: (x1 - x0) * width, height: (y1 - y0) * height}}>
      <SoftShadow r={r} u={u} />
      <div style={{position: 'absolute', inset: 0, borderRadius: r, background: K.card, border: `${2 * u}px solid ${K.cardLine}`, overflow: 'hidden', fontFamily: F.ui, color: K.ink}}>
        <div style={{height: 64 * u, display: 'flex', alignItems: 'center', paddingLeft: 26 * u, gap: 12 * u}}>
          {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
            <div key={c} style={{width: 20 * u, height: 20 * u, borderRadius: 10 * u, background: c}} />
          ))}
          <div style={{marginLeft: 22 * u, color: K.greyLight, fontSize: 26 * u}}>‹ ›</div>
          {title ? <div style={{marginLeft: 14 * u, fontSize: 24 * u, fontWeight: 600}}>{title}</div> : null}
        </div>
        <div style={{position: 'absolute', top: 64 * u, left: 0, right: 0, bottom: 0, display: 'flex'}}>
          {sidebar ? (
            <div style={{width: 220 * u, background: '#ECEAE5', borderRight: `${1.5 * u}px solid ${K.cardLine}`, padding: `${12 * u}px ${20 * u}px`, fontSize: 19 * u, color: K.grey, lineHeight: 2}}>
              <div style={{fontSize: 15 * u}}>Favourites</div>
              {['AirDrop', 'Recents', 'Applications', 'Desktop', 'Documents', 'Downloads'].map((s) => (
                <div key={s} style={{color: s === 'Documents' ? K.ink : K.grey}}>{s}</div>
              ))}
            </div>
          ) : null}
          <div style={{flex: 1, position: 'relative'}}>{children}</div>
        </div>
      </div>
    </div>
  );
};
