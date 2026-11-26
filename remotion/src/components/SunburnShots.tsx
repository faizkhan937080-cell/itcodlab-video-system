// SUNBURN video wrapper (8bit_sciences): beats-sunburn-v1 -> one canvas per frame + pixel label, counter HUD, callout, glitch.
import React, {useLayoutEffect, useRef} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {H, PAL, S, W} from '../lib/pixel';
import {SBeat, sunAt, sunGlitch} from '../lib/sunburnState';
import {drawBeach} from './SunburnBeach';
import {drawSkin} from './SunburnSkin';
import {ScanlineGlitch} from './ScanlineGlitch';
import {DayCounter, PIXEL_FONT} from './DayCounter';
import {Callout} from './Callout';

export type SunburnProps = {start_s?: number; beats: SBeat[]};
export const SunburnShots: React.FC<SunburnProps> = ({start_s = 0, beats}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const ref = useRef<HTMLCanvasElement>(null);
  const T = start_s + frame / fps;
  const st = sunAt(T, beats);
  useLayoutEffect(() => {
    const c = ref.current!.getContext('2d')!;
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.clearRect(0, 0, W, H);
    if (st.mode === 'beach') drawBeach(c, st, T); else drawSkin(c, st, T);
  });
  const since = T - st.labelT0, typed = st.label.slice(0, Math.max(0, Math.floor((since * fps) / 2) + 1));
  const style = {fontFamily: PIXEL_FONT, color: '#fff', textShadow: '8px 8px 0 #000', textAlign: 'center' as const, position: 'absolute' as const, left: 0, right: 0};
  return (
    <AbsoluteFill style={{background: PAL.bg}}><AbsoluteFill style={{width: 1080, height: 1920, transformOrigin: '0 0', transform: `scale(${width / 1080})`}}>
      <ScanlineGlitch T={T} fps={fps} hits={sunGlitch(beats)} frame={frame}>
        <canvas ref={ref} width={W} height={H} style={{position: 'absolute', left: 0, top: 0, width: W * S, height: H * S, imageRendering: 'pixelated'}} />
        {st.hook >= 0 ? <div style={{...style, top: 300, fontSize: 96, transform: `translateY(${Math.floor(st.hook * 40) % 2 * 6}px)`}}>{typed}</div> : null}
        {st.hook < 0 && st.label && !st.callout ? <div style={{...style, top: 1560, fontSize: 64, opacity: Math.floor(since * 8) % 7 === 6 ? 0.4 : 1}}>{typed}</div> : null}
        <DayCounter label={st.counter} icon={st.icon ? 'ff' : null} sinceChangeS={since} />
        {st.callout ? <Callout text={st.label} ax={st.callout.x} ay={st.callout.y} sinceS={since} fps={fps} /> : null}
      </ScanlineGlitch>
    </AbsoluteFill></AbsoluteFill>
  );
};
