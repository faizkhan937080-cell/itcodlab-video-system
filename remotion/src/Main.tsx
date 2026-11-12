import React from 'react';
import {AbsoluteFill, Freeze, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {AudioTrack} from './components/AudioTrack';
import {Banner} from './components/Banner';
import {BarChart} from './components/BarChart';
import {Checklist} from './components/Checklist';
import {CleanBg, CleanCard} from './components/Clean';
import {Captions} from './components/Captions';
import {ExtCaptions} from './components/ExtCaptions';
import {EXT} from './ext';
import {NtBg, NtCard} from './components/Nt';
import {Counter} from './components/Counter';
import {Grain, Vignette} from './components/Grain';
import {ImageScene} from './components/ImageScene';
import {KineticText} from './components/KineticText';
import {AudioBars} from './components/AudioBars';
import {MedScene} from './components/MedScene';
import {MemeFx} from './components/MemeFx';
import {MemeText} from './components/MemeText';
import {Sticker} from './components/Sticker';
import {LottieScene} from './components/LottieScene';
import {LowerThird} from './components/LowerThird';
import {PaperCutout} from './components/PaperCutout';
import {Quote} from './components/Quote';
import {SplitCompare} from './components/SplitCompare';
import {Stroke} from './components/Stroke';
import {Title} from './components/Title';
import {VideoScene} from './components/VideoScene';
import {easeOut} from './lib/anim';
import {Colors, DEFAULT_COLORS, OverlayDef, Plan, SceneDef, sceneFrames, totalFrames} from './lib/types';
import {followAt, zoomAt} from './lib/zoom';

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
          transparent={p.transparent}
          reframePath={p.reframe_path}
          srcAspect={p.src_aspect}
          scale={p.scale}
          offsetY={p.offset_y}
          blend={p.blend}
          fade={p.fade}
          layout={p.layout}
        />
      );
    case 'clean_bg':
      return <CleanBg brand={p.brand} footer={p.footer} />;
    case 'clean_card':
      return <CleanCard {...p} />;
    case 'ext':
    case 'clone': {
      const C = EXT[p.component];
      if (!C) throw new Error(`component ${p.component} not in ext/REGISTRY`);
      return <C {...(p.props ?? {})} />;
    }
    case 'nt_bg':
      return <NtBg mode={p.mode} />;
    case 'nt_card':
      return <NtCard {...p} />;
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
    case 'lottie':
      return <LottieScene src={p.src ?? ''} size={p.size} x={p.x} y={p.y} loop={p.loop} speed={p.speed} />;
    case 'audio_bars':
      return <AudioBars src={p.src ?? ''} bars={p.bars} color={p.color} y={p.y} height={p.height} colors={colors} />;
    case 'meme_text':
      return <MemeText text={p.text ?? ''} position={p.position} color={p.color} colors={colors} />;
    case 'sticker':
      return <Sticker text={p.text ?? ''} x={p.x} y={p.y} size={p.size} rotateDeg={p.rotate_deg} />;
    case 'med':
      return <MedScene {...(p as any)} />;
    default:
      return null;
  }
};

/** A graphic over the scene. With `follow` it moves with the tracked subject (stroke: stretched over its box; others: shifted). */
const Overlay: React.FC<{ov: OverlayDef; colors: Colors}> = ({ov, colors}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = (ov.start_s ?? 0) + frame / fps;
  const f = followAt(ov.follow, t);
  const props = {...(ov.props ?? {})};
  if (ov.template === 'stroke') {
    const box = f ? {x: f.x, y: f.y, w: f.w, h: f.h} : ov.box;
    return <Stroke text={props.text} shape={props.shape ?? 'circle'} color={props.color} colors={colors} box={box} />;
  }
  const shift = f ? `translate(${(f.x - 0.5) * width}px, ${(f.y - 0.5) * height}px)` : undefined;
  return (
    <AbsoluteFill style={{transform: shift}}>
      <SceneBody scene={{id: 'overlay', duration_s: 1, template: ov.template, props}} colors={colors} />
    </AbsoluteFill>
  );
};

/** Intro animation of a scene (the transition into it). 'cut' = none. */
const SceneWrap: React.FC<{scene: SceneDef; colors: Colors; stepFps?: number}> = ({scene, colors, stepFps}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const t = scene.transition_in ?? {type: 'cut'};
  const dur = Math.max(1, Math.round((t.duration_s ?? 0.4) * fps));
  const prog = easeOut(frame, 0, dur);
  // stop-motion look: freeze the scene content on every Nth frame (never raw video: it must stay smooth)
  const step = stepFps && scene.template !== 'video' ? Math.max(1, Math.round(fps / stepFps)) : 1;
  let style: React.CSSProperties = {};
  if (t.type === 'fade') style = {opacity: prog};
  if (t.type === 'slide') style = {opacity: prog, transform: `translateX(${(1 - prog) * width * 0.12}px)`};
  if (t.type === 'zoom') style = {opacity: prog, transform: `scale(${1.15 - 0.15 * prog})`};
  if (t.type === 'wipe') style = {clipPath: `inset(0 ${(1 - prog) * 100}% 0 0)`};
  if (t.type === 'slide_up') style = {opacity: prog, transform: `translateY(${(1 - prog) * height * 0.1}px)`};
  if (t.type === 'flip') style = {opacity: prog, transform: `perspective(${width * 2}px) rotateY(${(1 - prog) * 70}deg)`};
  if (t.type === 'whip') style = {transform: `translateX(${(1 - prog) * width}px)`, filter: `blur(${(1 - prog) * 28}px)`};
  if (t.type === 'iris') style = {clipPath: `circle(${prog * 75}% at 50% 50%)`};
  if (t.type === 'clock_wipe') style = {WebkitMaskImage: `conic-gradient(#000 ${prog * 360}deg, transparent ${prog * 360}deg)`, maskImage: `conic-gradient(#000 ${prog * 360}deg, transparent ${prog * 360}deg)`};
  const z = zoomAt(scene.zoom, frame / fps);
  const zoomStyle: React.CSSProperties =
    scene.zoom && scene.zoom.length ? {transform: `scale(${z.scale})`, transformOrigin: `${z.x * 100}% ${z.y * 100}%`} : {};
  return (
    <AbsoluteFill style={style}>
      <AbsoluteFill style={zoomStyle}>
       <MemeFx fx={scene.fx}>
        {(scene.underlays ?? []).map((ov, i) => {
          const from = Math.round((ov.start_s ?? 0) * fps);
          const to = ov.end_s !== undefined ? Math.round(ov.end_s * fps) : Math.round(scene.duration_s * fps);
          return (
            <Sequence key={`un-${i}`} from={from} durationInFrames={Math.max(1, to - from)}>
              <Overlay ov={ov} colors={colors} />
            </Sequence>
          );
        })}
        {step > 1 ? (
          <Freeze frame={Math.floor(frame / step) * step}>
            <SceneBody scene={scene} colors={colors} />
          </Freeze>
        ) : (
          <SceneBody scene={scene} colors={colors} />
        )}
        {(scene.overlays ?? []).map((ov, i) => {
          const from = Math.round((ov.start_s ?? 0) * fps);
          const to = ov.end_s !== undefined ? Math.round(ov.end_s * fps) : Math.round(scene.duration_s * fps);
          return (
            <Sequence key={`ov-${i}`} from={from} durationInFrames={Math.max(1, to - from)}>
              <Overlay ov={ov} colors={colors} />
            </Sequence>
          );
        })}
       </MemeFx>
      </AbsoluteFill>
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
      {plan.scenes.map((scene, i) => {
        const frames = sceneFrames(scene.duration_s, fps);
        // overlapping transition of the NEXT scene: keep this scene on screen underneath it (timeline unchanged)
        const nx = plan.scenes[i + 1]?.transition_in;
        const tail = nx && nx.overlap && nx.type && nx.type !== 'cut' ? Math.max(1, Math.round((nx.duration_s ?? 0.4) * fps)) : 0;
        const el = (
          <Sequence key={scene.id} from={from} durationInFrames={frames + tail}>
            <SceneWrap scene={scene} colors={colors} stepFps={plan.step_fps} />
          </Sequence>
        );
        from += frames;
        return el;
      })}
      {plan.texture ? (
        <AbsoluteFill style={{mixBlendMode: plan.texture.blend ?? 'multiply', opacity: plan.texture.opacity ?? 0.35, pointerEvents: 'none'}}>
          <Img src={staticFile(plan.texture.src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>
      ) : null}
      {plan.captions && plan.captions.length ? (
        plan.caption_style?.look === 'ext' ? (
          <ExtCaptions captions={plan.captions} style={plan.caption_style as any} />
        ) : (
          <Captions captions={plan.captions} style={plan.caption_style} colors={colors} />
        )
      ) : null}
      {(plan.audio ?? []).map((t, i) => (
        <AudioTrack key={`audio-${i}`} track={t} totalFrames={totalFrames(plan)} />
      ))}
      {plan.grain ? <Grain src={plan.grain_src} /> : null}
      {plan.vignette ? <Vignette strength={plan.vignette} /> : null}
    </AbsoluteFill>
  );
};
