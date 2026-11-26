// 8bit_sciences bruise video: wires beats-v1.json into the pixel parts. scene 'skin' = b1..b12, scene 'end' = b13..b14.
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, glitchTimes, stateAt} from '../lib/eightbitState';
import {PAL, S} from '../lib/pixel';
import {PixelSkinSection} from './PixelSkinSection';
import {PixelActors} from './PixelActors';
import {ScanlineGlitch} from './ScanlineGlitch';
import {DayCounter, PIXEL_FONT} from './DayCounter';
import {Callout} from './Callout';
import {PixelScene} from './PixelScene';
import {SunburnShots} from './SunburnShots';

export type EightBitProps = {scene?: 'skin' | 'end' | 'sunburn'; start_s?: number; beats: Beat[]};

export const EightBitShots: React.FC<EightBitProps> = (props) => (props.scene === 'sunburn' ? <SunburnShots start_s={props.start_s} beats={props.beats as any} /> : <BruiseShots {...props} />);
const BruiseShots: React.FC<EightBitProps> = ({scene = 'skin', start_s = 0, beats}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const k = width / 1080; // art is designed at 1080x1920; scale up for 4K frames
  const T = start_s + frame / fps;
  const st = stateAt(T, beats);
  const dayStart = beats.filter((b) => b.counter && b.t[0] <= T).pop()?.t[0] ?? -1;
  const world = (
    <AbsoluteFill style={{background: PAL.bg}}>
      <PixelSkinSection state={st} />
      <PixelActors state={st} T={T} />
    </AbsoluteFill>
  );
  const b13 = beats.find((b) => b.id === 'b13')?.t[0] ?? 22.3;
  const b14 = beats.find((b) => b.id === 'b14')?.t[0] ?? 23.3;
  return (
    <AbsoluteFill style={{background: PAL.bg}}><AbsoluteFill style={{width: 1080, height: 1920, transformOrigin: '0 0', transform: `scale(${k})`}}>
    <ScanlineGlitch T={T} fps={fps} hits={glitchTimes(beats)} frame={frame}>
      {scene === 'end' ? <PixelScene t={T} zoom={world} healedAt={b13} outdoorAt={b14} /> : (
        <>
          {world}
          {st.hook >= 0 ? <div style={{position: 'absolute', left: 0, right: 0, top: 300, textAlign: 'center', fontFamily: PIXEL_FONT, fontSize: 110, color: '#fff', textShadow: '10px 10px 0 #000', transform: `translateY(${Math.floor(st.hook * 6) % 2 * 6}px)`}}>OUCH</div> : null}
          <DayCounter label={st.day} icon={st.icon} sinceChangeS={T - dayStart} />
          {st.callout ? <Callout text={st.callout.text} ax={st.callout.x} ay={st.callout.y} sinceS={T - st.callout.t0} fps={fps} /> : null}
        </>
      )}
    </ScanlineGlitch>
    </AbsoluteFill></AbsoluteFill>
  );
};
export {S};
