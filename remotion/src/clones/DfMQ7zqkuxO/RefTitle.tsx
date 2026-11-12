import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {F, unit} from './theme';

/** Series stinger (8.8-10.6 s): manila file folders on a dark desk, hard spotlight from top-left, a paper sheet with
 * red-brown typewriter lines ("Claude / Mastery / Episode no. 02"), slow push-in (~3 % over the shot). The desk
 * picture is a real photo from the asset library (never drawn). */
export const RefTitle: React.FC<{bg: string; lines: {text: string; size: number}[]; push?: number}> = ({bg, lines, push = 0.03}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const u = unit(width);
  const z = 1 + push * (frame / Math.max(1, durationInFrames));
  return (
    <AbsoluteFill style={{backgroundColor: '#0E0D0B', overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${z})`}}>
        <Img src={bg.startsWith('http') ? bg : staticFile(bg)} style={{width: '100%', height: '100%', objectFit: 'cover', filter: 'none'}} />
        <div style={{position: 'absolute', left: 0.12 * width, top: 0.4 * height, width: 0.76 * width, transform: 'rotate(-4deg)'}}>
          <div style={{textAlign: 'center', fontFamily: F.type, color: '#9A4A3A', opacity: 0.92}}>
            {lines.map((l, i) => (
              <div key={i} style={{fontSize: l.size * u, lineHeight: 1.1, marginTop: i ? 10 * u : 0}}>{l.text}</div>
            ))}
          </div>
        </div>
        <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 70% 45% at 52% 62%, rgba(0,0,0,0) 0%, rgba(0,0,0,0.35) 60%, rgba(0,0,0,0.78) 100%)'}} />
      </div>
    </AbsoluteFill>
  );
};
