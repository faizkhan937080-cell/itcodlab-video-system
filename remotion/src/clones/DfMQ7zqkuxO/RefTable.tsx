import React from 'react';
import {Img, staticFile, useVideoConfig} from 'remotion';
import {MacWindow} from './MacWindow';
import {Page} from './Page';
import {StepHeader} from './StepHeader';
import {TimedCheck, useIn} from './parts';
import {F, K, unit} from './theme';

type Row = {name: string; img?: string; what: string; why: string; check_s?: number | null};

/** "Step 2 Install the tools" table (37.5-43 s): straight on the cream page, 3 grey caps column heads, 5 rows,
 * logo + bold name | what | why | checkbox ticking one by one. layout split = top half, full = whole page. */
export const RefTable: React.FC<{step: string; title: string; heads: [string, string, string]; rows: Row[]; layout?: 'split' | 'full'; plate?: string; crumb?: string}> = ({step, title, heads, rows, layout = 'split', plate, crumb}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  const rowH = (layout === 'split' ? 0.064 : 0.09) * height;
  // the reference never shows bare text on the page in split shots: content sits in a white app window
  return (
    <>
      <Page mode={layout} plate={plate} />
      <StepHeader step={step} title={title} />
      <MacWindow box={[0.03, 0.072, 0.97, layout === 'split' ? 0.478 : 0.8]} title={crumb ?? title}>
      <div style={{position: 'absolute', left: 0.04 * width, right: 0.04 * width, top: 0.012 * height, fontFamily: F.ui, color: K.ink}}>
        <div style={{display: 'flex', fontSize: 17 * u, letterSpacing: 1.2 * u, color: K.greyLight, fontWeight: 600, marginBottom: 14 * u, borderBottom: `${1.5 * u}px solid ${K.cardLine}`, paddingBottom: 10 * u}}>
          <div style={{width: '36%'}}>{heads[0]}</div>
          <div style={{width: '26%'}}>{heads[1]}</div>
          <div style={{flex: 1}}>{heads[2]}</div>
        </div>
        {rows.map((r, i) => (
          <RowView key={i} r={r} h={rowH} u={u} i={i} />
        ))}
      </div>
      </MacWindow>
    </>
  );
};

const RowView: React.FC<{r: Row; h: number; u: number; i: number}> = ({r, h, u, i}) => {
  const k = useIn(0.04 * i);
  return (
    <div style={{display: 'flex', alignItems: 'center', height: h, opacity: k, transform: `translateY(${(1 - k) * 10 * u}px)`}}>
      <div style={{width: '36%', display: 'flex', alignItems: 'center', gap: 18 * u}}>
        {r.img ? <Img src={r.img.startsWith('http') ? r.img : staticFile(r.img)} style={{width: 46 * u, height: 46 * u, borderRadius: 10 * u, objectFit: 'cover'}} /> : null}
        <div style={{fontSize: 32 * u, fontWeight: 700}}>{r.name}</div>
      </div>
      <div style={{width: '26%', fontSize: 23 * u, color: '#55524D'}}>{r.what}</div>
      <div style={{flex: 1, fontSize: 21 * u, color: K.grey}}>{r.why}</div>
      <TimedCheck at={r.check_s ?? null} size={36 * u} />
    </div>
  );
};
