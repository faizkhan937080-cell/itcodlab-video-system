import React from 'react';
import {Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {F, K, unit} from './theme';

/** Wall of reels (0-5 s): 3 rows of rounded 9:16 tiles on the cream page with a grey @handle under each, rows
 * drifting sideways (top and bottom one way, middle the other). layout split = top half (talking head below). */
export const RefWall: React.FC<{images: string[]; titles?: string[]; handles?: string[]; speed?: number; layout?: 'split' | 'full'; plate?: string}> = ({images, titles = [], handles = [], speed = 70, layout = 'split', plate}) => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const u = unit(width);
  const areaH = layout === 'split' ? 0.5 * height : height;
  const tileH = areaH * 0.31;
  const tileW = tileH * 9 / 16;
  const gap = 0.025 * width;
  const rowsY = [0.02, 0.36, 0.7].map((f) => f * areaH);
  return (
    <>
      <Page mode={layout} plate={plate} />
      <div style={{position: 'absolute', left: 0, top: 0, width, height: areaH, overflow: 'hidden'}}>
        {rowsY.map((y, r) => {
          const dir = r === 1 ? -1 : 1;
          const off = ((frame / fps) * speed * u * dir) % (tileW + gap);
          return (
            <div key={r} style={{position: 'absolute', top: y - (r === 0 ? tileH * 0.55 : 0), left: -tileW + off, display: 'flex', gap}}>
              {Array.from({length: 9}).map((_, i) => {
                const k = (r * 3 + i) % Math.max(1, images.length);
                return (
                  <div key={i} style={{width: tileW}}>
                    <div style={{width: tileW, height: tileH, borderRadius: 16 * u, overflow: 'hidden', border: `${1.5 * u}px solid ${K.cardLine}`, background: K.card, position: 'relative'}}>
                      {/* reference tiles (0.5-5 s) are reel covers: cream card, bold title on top, picture below */}
                      {titles.length && (r + i) % 3 !== 1 ? (
                        <div style={{height: '38%', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: `0 ${8 * u}px`, fontFamily: F.sans, fontWeight: 800, fontSize: 22 * u, lineHeight: 1.05, color: K.ink, textTransform: 'uppercase'}}>
                          {titles[(r * 5 + i) % titles.length]}
                        </div>
                      ) : null}
                      {images.length ? (
                        <Img src={images[k].startsWith('http') ? images[k] : staticFile(images[k])} style={{width: '100%', height: titles.length && (r + i) % 3 !== 1 ? '62%' : '100%', objectFit: 'cover', display: 'block'}} />
                      ) : null}
                    </div>
                    <div style={{textAlign: 'center', fontFamily: F.ui, fontSize: 15 * u, color: K.greyLight, marginTop: 8 * u}}>{handles[k % Math.max(1, handles.length)] ?? ''}</div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </>
  );
};
