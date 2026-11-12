import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Page} from './Page';
import {SoftShadow, Folder, useIn} from './parts';
import {F, K, unit} from './theme';

type Node = {label: string; sub?: string; at_s?: number; active_s?: number; children?: Node[]};

/** Folder tree on the cream page (55.9-63.3 s): white root chip (folder + bold name + grey sub), thin grey trunk,
 * dimmed children; the active one gets a dark-outlined white chip and its children grow out under it. */
export const RefTree: React.FC<{root: {label: string; sub?: string}; items: Node[]; layout?: 'split' | 'full'; plate?: string}> = ({root, items, layout = 'full', plate}) => {
  const {width, height} = useVideoConfig();
  const u = unit(width);
  const rows: {n: Node; depth: number}[] = [];
  const walk = (ns: Node[], d: number) => ns.forEach((n) => { rows.push({n, depth: d}); if (n.children) walk(n.children, d + 1); });
  walk(items, 1);
  const y0 = (layout === 'full' ? 0.155 : 0.06) * height;
  const step = (layout === 'full' ? 0.06 : 0.05) * height;
  return (
    <>
      <Page mode={layout} plate={plate} />
      <div style={{position: 'absolute', left: 0, top: 0, width, height, fontFamily: F.sans, color: K.ink}}>
        <div style={{position: 'absolute', left: 0.08 * width, top: y0}}>
          <div style={{position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 18 * u, padding: `${16 * u}px ${26 * u}px`}}>
            <SoftShadow r={18 * u} u={u} />
            <div style={{position: 'absolute', inset: 0, borderRadius: 18 * u, background: '#FFFFFF', border: `${1.5 * u}px solid ${K.cardLine}`}} />
            <div style={{position: 'relative'}}><Folder size={64 * u} /></div>
            <div style={{position: 'relative'}}>
              <div style={{fontSize: 40 * u, fontWeight: 800, letterSpacing: -0.6 * u}}>{root.label}</div>
              {root.sub ? <div style={{fontSize: 18 * u, color: K.grey}}>{root.sub}</div> : null}
            </div>
          </div>
        </div>
        <div style={{position: 'absolute', left: 0.155 * width, top: y0 + 105 * u, width: 2 * u, height: rows.length * step, background: '#CFCBC2'}} />
        {rows.map((r, i) => (
          <TreeRow key={i} r={r.n} depth={r.depth} y={y0 + 120 * u + i * step} u={u} width={width} />
        ))}
      </div>
    </>
  );
};

const TreeRow: React.FC<{r: Node; depth: number; y: number; u: number; width: number}> = ({r, depth, y, u, width}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const k = useIn(r.at_s ?? 0);
  const active = r.active_s !== undefined && frame >= r.active_s * fps;
  const a = r.active_s !== undefined ? interpolate(frame, [r.active_s * fps, r.active_s * fps + 8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  const x = 0.155 * width + (depth - 1) * 0.075 * width;
  return (
    <div style={{position: 'absolute', left: x, top: y, display: 'flex', alignItems: 'center', opacity: k}}>
      <div style={{width: 0.06 * width, height: 2 * u, background: '#CFCBC2'}} />
      <div style={{position: 'relative', display: 'flex', alignItems: 'center', gap: 12 * u, padding: `${8 * u}px ${14 * u}px`}}>
        <div style={{position: 'absolute', inset: 0, borderRadius: 12 * u, background: '#FFFFFF', border: `${2 * u}px solid #3A3733`, opacity: a}} />
        <div style={{position: 'relative'}}><Folder size={40 * u} dim={active ? 1 : 0.55} color={active ? '#5DAEF2' : '#B8C9D9'} /></div>
        <div style={{position: 'relative'}}>
          <div style={{fontSize: 26 * u, fontWeight: 700, color: active ? K.ink : '#9C9890'}}>{r.label}</div>
          {r.sub ? <div style={{fontSize: 15 * u, color: K.grey}}>{r.sub}</div> : null}
        </div>
      </div>
    </div>
  );
};
