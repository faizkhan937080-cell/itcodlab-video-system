import React from 'react';
import {Img, staticFile, useVideoConfig} from 'remotion';
import {MacWindow} from './MacWindow';
import {Page} from './Page';
import {StepHeader} from './StepHeader';
import {useIn} from './parts';
import {F, K, unit} from './theme';

type Item = {img: string; name: string; at_s?: number};

/** Finder window with a growing thumbnail grid (Step 3 "Teach it your style", 43.9-46.7 s): sidebar, breadcrumb,
 * "This folder is empty" until the first file lands, files drop in one by one (3 per row) with small names. */
export const RefFinder: React.FC<{step: string; title: string; crumb: string; items: Item[]; layout?: 'split' | 'full'; plate?: string}> = ({step, title, crumb, items, layout = 'split', plate}) => {
  const {width} = useVideoConfig();
  const u = unit(width);
  return (
    <>
      <Page mode={layout} plate={plate} />
      <StepHeader step={step} title={title} />
      <MacWindow box={[0.02, 0.06, 0.98, layout === 'split' ? 0.47 : 0.8]} title={crumb} sidebar>
        <Empty items={items} u={u} />
        <div style={{display: 'flex', flexWrap: 'wrap', gap: 22 * u, padding: 24 * u}}>
          {items.map((it, i) => (
            <Thumb key={i} it={it} u={u} />
          ))}
        </div>
      </MacWindow>
    </>
  );
};

const Empty: React.FC<{items: Item[]; u: number}> = ({items, u}) => {
  const k = useIn(items.length ? items[0].at_s ?? 0 : 1e6);
  return <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: F.ui, fontSize: 20 * u, color: K.greyLight, opacity: 1 - k}}>This folder is empty</div>;
};

const Thumb: React.FC<{it: Item; u: number}> = ({it, u}) => {
  const k = useIn(it.at_s ?? 0);
  return (
    <div style={{width: 196 * u, opacity: k, transform: `translateY(${(1 - k) * -14 * u}px)`}}>
      <div style={{width: 196 * u, height: 170 * u, borderRadius: 10 * u, overflow: 'hidden', border: `${1.5 * u}px solid ${K.cardLine}`}}>
        <Img src={it.img.startsWith('http') ? it.img : staticFile(it.img)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </div>
      <div style={{textAlign: 'center', fontFamily: F.ui, fontSize: 15 * u, color: '#55524D', marginTop: 6 * u, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{it.name}</div>
    </div>
  );
};
