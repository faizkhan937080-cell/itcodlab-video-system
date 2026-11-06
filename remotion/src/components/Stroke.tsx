import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {easeOut, unit} from '../lib/anim';
import {Colors} from '../lib/types';

const PATHS: Record<string, string> = {
  underline: 'M20 200 C 200 170, 400 230, 600 190 S 900 210, 980 180',
  circle:
    'M500 40 C 800 20, 960 120, 940 160 C 920 260, 600 290, 400 270 C 150 250, 40 180, 80 120 C 120 50, 380 25, 560 45',
  arrow: 'M40 200 C 300 120, 600 280, 900 150 M900 150 L820 120 M900 150 L830 215',
  scribble: 'M40 60 L960 90 L60 130 L940 160 L80 200 L920 230',
};

/** Hand-drawn stroke that draws itself over a text. props: text, shape (underline|circle|arrow|scribble), color (brand key). No filters. */
export const Stroke: React.FC<{text?: string; shape?: string; color?: string; colors: Colors; box?: {x: number; y: number; w: number; h: number}}> = ({
  text,
  shape = 'underline',
  color = 'coral',
  colors,
  box,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const u = unit(width, height);
  const prog = easeOut(frame, 8, 8 + 26);
  const d = PATHS[shape] ?? PATHS.underline;
  if (box) {
    // follows a tracked subject: the shape is stretched over the box (x,y = centre, fractions of the frame), 25% wider than the subject
    const k = 1.25;
    return (
      <AbsoluteFill>
        <svg viewBox="0 0 1000 300" preserveAspectRatio="none" style={{position: 'absolute', left: `${(box.x - (box.w * k) / 2) * 100}%`, top: `${(box.y - (box.h * k) / 2) * 100}%`, width: `${box.w * k * 100}%`, height: `${box.h * k * 100}%`}}>
          <path d={d} pathLength={1} fill="none" stroke={colors[color] ?? colors.coral} strokeWidth={14} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={1} strokeDashoffset={1 - prog} />
        </svg>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div style={{position: 'relative', width: 920 * u, height: 420 * u, display: 'flex', justifyContent: 'center', alignItems: 'center'}}>
        {text ? (
          <div style={{color: colors.white, fontSize: 130 * u, fontWeight: 900, textAlign: 'center', lineHeight: 1.05, opacity: easeOut(frame, 0, 10)}}>
            {text}
          </div>
        ) : null}
        <svg viewBox="0 0 1000 300" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} preserveAspectRatio="none">
          <path
            d={d}
            pathLength={1}
            fill="none"
            stroke={colors[color] ?? colors.coral}
            strokeWidth={14}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={1}
            strokeDashoffset={1 - prog}
          />
        </svg>
      </div>
    </AbsoluteFill>
  );
};
