import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, staticFile, useDelayRender} from 'remotion';
import {Lottie, LottieAnimationData} from '@remotion/lottie';

/** A Lottie animation from the library (assets/library/motion/*.json). props: src, size (0.1..1 of the short side), x, y (0..1), loop, speed. */
export const LottieScene: React.FC<{src: string; size?: number; x?: number; y?: number; loop?: boolean; speed?: number}> = ({
  src,
  size = 0.6,
  x = 0.5,
  y = 0.5,
  loop = true,
  speed = 1,
}) => {
  const {delayRender, continueRender} = useDelayRender();
  const [handle] = useState(() => delayRender(`lottie ${src}`));
  const [data, setData] = useState<LottieAnimationData | null>(null);
  useEffect(() => {
    fetch(staticFile(src))
      .then((r) => r.json())
      .then((j) => {
        setData(j);
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [src, handle, continueRender]);
  if (!data) return null;
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: `${x * 100}%`,
          top: `${y * 100}%`,
          width: `${size * 100}vmin`,
          height: `${size * 100}vmin`,
          transform: 'translate(-50%, -50%)',
        }}
      >
        <Lottie animationData={data} loop={loop} playbackRate={speed} style={{width: '100%', height: '100%'}} />
      </div>
    </AbsoluteFill>
  );
};
