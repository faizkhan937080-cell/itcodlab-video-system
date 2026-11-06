import React from 'react';
import {AbsoluteFill, Freeze, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {AudioTrack} from './components/AudioTrack';
import {Banner} from './components/Banner';
import {BarChart} from './components/BarChart';
import {Checklist} from './components/Checklist';
import {Captions} from './components/Captions';
import {Counter} from './components/Counter';
import {Grain} from './components/Grain';
import {ImageScene} from './components/ImageScene';
import {KineticText} from './components/KineticText';
import {LowerThird} from './components/LowerThird';
import {PaperCutout} from './components/PaperCutout';
import {Quote} from './components/Quote';
import {SplitCompare} from './components/SplitCompare';
import {Stroke} from './components/Stroke';
import {Title} from './components/Title';
import {VideoScene} from './components/VideoScene';
import {easeOut} from './lib/anim';
import {Colors, DEFAULT_COLORS, Plan, SceneDef, sceneFrames, totalFrames} from './lib/types';

const SceneBody: React.FC<{scene: SceneDef; colors: Colors}> = ({scene, colors}) => {
  const p = scene.props ?? {};
  switch (scene.template) {
    case 'title':
      return <Title text={p.text ?? ''} subtitle={p.subtitle} colors={colors} />;
    case 'kinetic_text':
      return <KineticText text={p.text ?? ''} highlight={p.highlight} colors={colors} />;
    case 'banner':
      return <Banner headline={p.headline ?? ''} sub={p.sub} tag={p.tag} colors={colors} />;
    case 'image':
      return <ImageScene src={p.src} caption={p.caption} colors={colors} />;
    case 'lower_third':
      return <LowerThird name={p.name ?? ''} role={p.role} colors={colors} />;
    case 'video':
      return (
        <VideoScene
          src={p.src}
          trimStartS={p.trim_start_s}
          trimEndS={p.trim_end_s}
          fit={p.fit}
          muted={p.muted}
          volume={p.volume}
        />
      );
    case 'counter':
      return (
        <Counter
          value={Number(p.value ?? 0)}
          prefix={p.prefix}
          suffix={p.suffix}
          decimals={p.decimals}
          label={p.label}
          colors={colors}
        />
      );
    case 'bar_chart':
      return <BarChart title={p.title} items={Array.isArray(p.items) ? p.items : []} suffix={p.suffix} colors={colors} />;
    case 'checklist':
      return <Checklist title={p.title} items={Array.isArray(p.items) ? p.items : []} colors={colors} />;
    case 'split_compare':
      return <SplitCompare left={p.left ?? {title: ''}} right={p.right ?? {title: ''}} colors={colors} />;
    case 'quote':
      return <Quote text={p.text ?? ''} author={p.author} colors={colors} />;
    case 'paper_cutout':
      return (
        <PaperCutout src={p.src ?? ''} caption={p.caption} rotateDeg={p.rotate_deg} size={p.size} seed={p.seed} colors={colors} />
      );
    case 'stroke':
      return <Stroke text={p.text} shape={p.shape} color={p.color} colors={colors} />;
    default:
      return null;
  }
};

/** Intro animation of a scene (the transition into it). 'cut' = none. */
const SceneWrap: React.FC<{scene: SceneDef; colors: Colors; stepFps?: number}> = ({scene, colors, stepFps}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const t = scene.transition_in ?? {type: 'cut'};
  const dur = Math.max(1, Math.round((t.duration_s ?? 0.4) * fps));
  const prog = easeOut(frame, 0, dur);
  // stop-motion look: freeze the scene content on every Nth frame (never raw video: it must stay smooth)
  const step = stepFps && scene.template !== 'video' ? Math.max(1, Math.round(fps / stepFps)) : 1;
  let style: React.CSSProperties = {};
  if (t.type === 'fade') style = {opacity: prog};
  if (t.type === 'slide') style = {opacity: prog, transform: `translateX(${(1 - prog) * width * 0.12}px)`};
  if (t.type === 'zoom') style = {opacity: prog, transform: `scale(${1.15 - 0.15 * prog})`};
  return (
    <AbsoluteFill style={style}>
      {step > 1 ? (
        <Freeze frame={Math.floor(frame / step) * step}>
          <SceneBody scene={scene} colors={colors} />
        </Freeze>
      ) : (
        <SceneBody scene={scene} colors={colors} />
      )}
    </AbsoluteFill>
  );
};

export const Main: React.FC<Plan> = (plan) => {
  const {fps} = useVideoConfig();
  const colors: Colors = {...DEFAULT_COLORS, ...(plan.brand?.colors ?? {})};
  let from = 0;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: colors.navy,
        fontFamily: plan.brand?.font ?? 'Inter, "Helvetica Neue", Arial, sans-serif',
      }}
    >
      {plan.scenes.map((scene) => {
        const frames = sceneFrames(scene.duration_s, fps);
        const el = (
          <Sequence key={scene.id} from={from} durationInFrames={frames}>
            <SceneWrap scene={scene} colors={colors} stepFps={plan.step_fps} />
          </Sequence>
        );
        from += frames;
        return el;
      })}
      {plan.captions && plan.captions.length ? (
        <Captions captions={plan.captions} style={plan.caption_style} colors={colors} />
      ) : null}
      {(plan.audio ?? []).map((t, i) => (
        <AudioTrack key={`audio-${i}`} track={t} totalFrames={totalFrames(plan)} />
      ))}
      {plan.grain ? <Grain /> : null}
    </AbsoluteFill>
  );
};
