// Skills testing video: one part per skill, each drawn with that skill's own method. Every motion is driven by useCurrentFrame (no useFrame).
// Honesty rule: a part that cannot run says NOT TESTED + reason on screen. The skill name stays on screen for the whole part.
import React from 'react';
import {AbsoluteFill, Sequence, Solid, interpolate, random, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {Lottie} from '@remotion/lottie';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {slide} from '@remotion/transitions/slide';
import {lightLeak} from '@remotion/effects/light-leak';
import {HtmlInCanvasMotionBlur} from '@remotion/motion-blur';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {FONT} from './MedScene';

export type SkillTestProps = {
  part: number;
  name: string; // skill name shown on screen for the whole part
  status: 'tested' | 'not_tested';
  note?: string; // bottom line: what is shown / why not tested
  reason?: string[]; // not_tested: reason lines
  hook?: string; // part 7: the hook line
  beats?: string[]; // part 6: sub-skill labels
  beat_status?: ('tested' | 'not_tested')[]; // part 6: per sub-skill
};

const wave = (t: number, period: number, phase = 0) => Math.sin(2 * Math.PI * (t / period + phase));
const loop = (t: number, period: number, phase = 0) => (((t / period + phase) % 1) + 1) % 1;
const ease = (q: number) => 1 - (1 - Math.min(1, Math.max(0, q))) ** 3;
type V3 = [number, number, number];

// ---------- shared overlay: skill name + status for the whole part ----------
const Overlay: React.FC<SkillTestProps & {t: number; beat?: number}> = ({name, status, note, part, t, beat, beats, beat_status}) => {
  const ok = status === 'tested';
  const bs = beat !== undefined && beat_status ? beat_status[beat] : undefined;
  const shown = bs ?? status;
  return (
    <>
      <div style={{position: 'absolute', left: 40, right: 40, top: 70, textAlign: 'center', fontFamily: FONT}}>
        <div style={{display: 'inline-block', maxWidth: 1000, background: 'rgba(8,10,20,0.88)', color: '#FFE066', border: '5px solid #FFE066', borderRadius: 26, padding: '14px 34px', fontSize: name.length > 34 ? 46 : 64, fontWeight: 900, lineHeight: 1.1}}>
          {name}
        </div>
        <div style={{marginTop: 18}}>
          <span style={{display: 'inline-block', background: shown === 'tested' ? '#1E9E4A' : '#D62B2B', color: '#fff', borderRadius: 18, padding: '8px 28px', fontSize: 46, fontWeight: 900, letterSpacing: 2}}>
            {shown === 'tested' ? 'TESTED' : 'NOT TESTED'}
          </span>
        </div>
        {beats ? (
          <div style={{marginTop: 16, display: 'flex', justifyContent: 'center', gap: 12}}>
            {beats.map((b, i) => (
              <span key={b} style={{background: i === beat ? '#FFE066' : 'rgba(8,10,20,0.75)', color: i === beat ? '#111' : '#BBB', border: '3px solid #FFE066', borderRadius: 14, padding: '6px 16px', fontSize: 34, fontWeight: 800}}>{b}</span>
            ))}
          </div>
        ) : null}
      </div>
      {note ? (
        <div style={{position: 'absolute', left: 50, right: 50, bottom: 150, textAlign: 'center', fontFamily: FONT, fontSize: 40, fontWeight: 800, color: '#fff', textShadow: '0 3px 10px #000, 0 0 4px #000', opacity: ease(t / 0.5)}}>
          {note}
        </div>
      ) : null}
      <div style={{position: 'absolute', right: 36, top: 36, fontFamily: FONT, fontSize: 30, fontWeight: 800, color: '#fff', opacity: 0.8}}>{part}/7</div>
      {ok ? null : null}
    </>
  );
};

// ---------- 1. claude-animated-shorts: flat cartoon character in a painted 3D street, ink outlines (three.js) ----------
const Toon: React.FC<{g: React.ReactNode; color: string; pos?: V3; rot?: V3; scale?: V3; ink?: number}> = ({g, color, pos = [0, 0, 0], rot = [0, 0, 0], scale = [1, 1, 1], ink = 1.07}) => (
  <group position={pos} rotation={rot} scale={scale}>
    <mesh>{g}<meshToonMaterial color={color} /></mesh>
    <mesh scale={ink}>{g}<meshBasicMaterial color="#15121C" side={THREE.BackSide} /></mesh>
  </group>
);
const HOUSE = ['#FF7A59', '#FFC145', '#5BC0EB', '#9BC53D', '#E55CA7', '#8E7DFF'];
const CartoonStreet: React.FC<{t: number}> = ({t}) => {
  const {width, height} = useVideoConfig();
  const swing = Math.sin(t * 8) * 0.6;
  const bob = Math.abs(Math.sin(t * 8)) * 0.1;
  const camX = Math.sin(t * 0.7) * 1.6;
  return (
    <ThreeCanvas width={width} height={height} camera={{fov: 42, position: [camX, 2.4, 8.6], near: 0.1, far: 60}} style={{position: 'absolute', inset: 0}}>
      <CamLook x={camX} />
      <color attach="background" args={['#8FD8FF']} />
      <fog attach="fog" args={['#8FD8FF', 14, 28]} />
      <ambientLight intensity={1.1} />
      <directionalLight position={[4, 8, 5]} intensity={1.5} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, -8]}><planeGeometry args={[40, 40]} /><meshToonMaterial color="#79D36B" /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, -8]}><planeGeometry args={[2.6, 40]} /><meshToonMaterial color="#5A5568" /></mesh>
      {Array.from({length: 14}, (_, i) => {
        const z = -18 + ((i * 1.8 + t * 2.4) % 25.2);
        const side = i % 2 ? 1 : -1;
        const c = HOUSE[i % HOUSE.length];
        return (
          <group key={i}>
            <Toon g={<boxGeometry args={[1.5, 1.4, 1.5]} />} color={c} pos={[side * 2.6, 0.7, z]} />
            <Toon g={<coneGeometry args={[1.25, 0.9, 4]} />} color="#C0392B" pos={[side * 2.6, 1.85, z]} rot={[0, Math.PI / 4, 0]} />
            <Toon g={<boxGeometry args={[0.35, 0.6, 0.05]} />} color="#FFF3B0" pos={[side * 1.84, 0.4, z]} rot={[0, Math.PI / 2, 0]} ink={1.15} />
          </group>
        );
      })}
      {Array.from({length: 4}, (_, i) => (
        <Toon key={i} g={<sphereGeometry args={[0.9, 16, 12]} />} color="#FFFFFF" pos={[-6 + loop(t, 18, i * 0.26) * 12, 6 + (i % 2), -8 - i]} scale={[1.6, 0.8, 1]} />
      ))}
      <Toon g={<sphereGeometry args={[1.2, 20, 14]} />} color="#FFD93D" pos={[3.5, 5.5, -16]} />
      {/* character: bean body, round head, swinging arms and legs */}
      <group position={[0, bob, 0]}>
        <Toon g={<capsuleGeometry args={[0.3, 0.55, 4, 14]} />} color="#FF6B35" pos={[0, 1.0, 0]} />
        <Toon g={<sphereGeometry args={[0.38, 20, 16]} />} color="#FFD7B5" pos={[0, 1.78, 0]} />
        <Toon g={<sphereGeometry args={[0.07, 10, 8]} />} color="#15121C" pos={[-0.13, 1.82, 0.34]} ink={1.0} />
        <Toon g={<sphereGeometry args={[0.07, 10, 8]} />} color="#15121C" pos={[0.13, 1.82, 0.34]} ink={1.0} />
        <Toon g={<coneGeometry args={[0.4, 0.34, 16]} />} color="#2F6FED" pos={[0, 2.2, 0]} />
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.3, 1.25, 0]} rotation={[swing * s, 0, s * 0.1]}>
            <Toon g={<capsuleGeometry args={[0.09, 0.45, 4, 10]} />} color="#FFD7B5" pos={[0, -0.28, 0]} />
          </group>
        ))}
        {[-1, 1].map((s) => (
          <group key={s} position={[s * 0.15, 0.55, 0]} rotation={[-swing * s, 0, 0]}>
            <Toon g={<capsuleGeometry args={[0.1, 0.4, 4, 10]} />} color="#2B2D42" pos={[0, -0.25, 0]} />
          </group>
        ))}
      </group>
    </ThreeCanvas>
  );
};
const CamLook: React.FC<{x: number}> = ({x}) => {
  // keeps the camera aimed at the character each frame (frame-driven: x comes from the frame)
  const {camera} = useThree();
  camera.position.x = x;
  camera.lookAt(0, 1.2, 0);
  return null;
};

// ---------- 2. claude-blender-skills: NOT TESTED card ----------
const BlenderCard: React.FC<{t: number; reason: string[]}> = ({t, reason}) => {
  const q = ease((t - 0.25) / 0.3);
  const scale = 3 - 2 * q + (q >= 1 ? Math.max(0, 0.12 * Math.sin((t - 0.55) * 22) * Math.exp(-(t - 0.55) * 6)) : 0);
  const shake = t > 0.55 && t < 0.85 ? Math.sin(t * 90) * 9 : 0;
  return (
    <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 45%, #2A1F3D 0%, #0B0814 75%)'}}>
      <div style={{position: 'absolute', left: 140, right: 140, top: 520, height: 520, border: '6px dashed #7A6AA8', borderRadius: 24, opacity: 0.7, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: 30, boxSizing: 'border-box', fontFamily: FONT, color: '#7A6AA8', fontSize: 40, fontWeight: 800}}>
        yahan Blender ka shot aata
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 640, textAlign: 'center', transform: `translateX(${shake}px) rotate(-8deg) scale(${scale})`, opacity: q, fontFamily: FONT, fontWeight: 900, fontSize: 150, color: '#FF3B30', textShadow: '0 0 30px #FF3B30', WebkitTextStroke: '4px #fff'}}>
        NOT TESTED
      </div>
      <div style={{position: 'absolute', left: 80, right: 80, top: 1120, fontFamily: FONT, fontSize: 48, fontWeight: 800, color: '#fff', textAlign: 'center', lineHeight: 1.35}}>
        {reason.map((r, i) => <div key={i} style={{opacity: ease((t - 1.1 - i * 0.6) / 0.35), transform: `translateY(${(1 - ease((t - 1.1 - i * 0.6) / 0.35)) * 24}px)`}}>{r}</div>)}
      </div>
    </AbsoluteFill>
  );
};

// ---------- 3. stickman-video-director (Code Engine B1: minimal line art, boiling line) ----------
const Stickman: React.FC<{t: number}> = ({t}) => {
  const walking = t < 4.0;
  const x = interpolate(t, [0.2, 4.0], [200, 540], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const sw = walking ? Math.sin(t * 9) * 28 : 0;
  const bounce = walking ? Math.abs(Math.sin(t * 9)) * 10 : 0;
  const jit = (k: number) => (random(`boil-${Math.floor(t * 8)}-${k}`) - 0.5) * 4;
  const rad = (d: number) => (d * Math.PI) / 180;
  const hipY = 1130 - bounce, shY = hipY - 190;
  const limb = (x0: number, y0: number, a1: number, a2: number, l1: number, l2: number, k: number) => {
    const x1 = x0 + Math.sin(rad(a1)) * l1, y1 = y0 + Math.cos(rad(a1)) * l1;
    const x2 = x1 + Math.sin(rad(a2)) * l2, y2 = y1 + Math.cos(rad(a2)) * l2;
    return `M ${x0 + jit(k)} ${y0 + jit(k + 1)} L ${x1 + jit(k + 2)} ${y1 + jit(k + 3)} L ${x2 + jit(k + 4)} ${y2 + jit(k + 5)}`;
  };
  const bub = ease((t - 4.3) / 0.25);
  return (
    <AbsoluteFill style={{background: '#F6F1E7'}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" fill="none" stroke="#111" strokeWidth={11} strokeLinecap="round" strokeLinejoin="round">
        <path d={`M 60 1280 L 1020 1280`} />
        <g transform="translate(900 470)"><circle r={62} /><g>{Array.from({length: 8}, (_, i) => <path key={i} d={`M ${Math.cos(i * 0.785 + t) * 88} ${Math.sin(i * 0.785 + t) * 88} l ${Math.cos(i * 0.785 + t) * 34} ${Math.sin(i * 0.785 + t) * 34}`} />)}</g></g>
        <g transform={`translate(${x - 540} 0)`}>
          <circle cx={540 + jit(40)} cy={shY - 70} r={72} />
          <path d={`M 540 ${shY} L 540 ${hipY}`} />
          <path d={limb(540, shY + 20, -sw * 1.2 - 15, -sw * 0.6 - 10, 100, 95, 0)} />
          <path d={limb(540, shY + 20, walking ? sw * 1.2 + 15 : 150 + Math.sin((t - 4.0) * 9) * 20, walking ? sw * 0.6 + 10 : 185 + Math.sin((t - 4.0) * 9) * 35, 100, 95, 10)} />
          <path d={limb(540, hipY, sw, sw * 0.4, 130, 130, 20)} />
          <path d={limb(540, hipY, -sw, -sw * 0.4 + 4, 130, 130, 30)} />
          <circle cx={520} cy={shY - 82} r={5} fill="#111" /><circle cx={562} cy={shY - 82} r={5} fill="#111" />
          <path d={`M 520 ${shY - 52} Q 541 ${shY - 36} 562 ${shY - 52}`} />
        </g>
      </svg>
      <div style={{position: 'absolute', left: x - 90, top: 640, transform: `scale(${bub})`, transformOrigin: '30% 100%', background: '#fff', border: '8px solid #111', borderRadius: 40, padding: '14px 36px', fontFamily: FONT, fontSize: 64, fontWeight: 900, color: '#111'}}>Namaste!</div>
    </AbsoluteFill>
  );
};

// ---------- 4. rossark-motion-skill: a drawn plant that feels alive (MOTION.md: pivots, phase delay, small amplitude, seeded loops) ----------
const LivingPlant: React.FC<{t: number}> = ({t}) => {
  const bx = 540, by = 1380;
  const pts: {x: number; y: number; a: number}[] = [{x: bx, y: by, a: 0}];
  let a = 0, x = bx, y = by;
  for (let k = 0; k < 6; k++) {
    a += wave(t, 6, k * 0.07) * 1.8 + (k - 2.5) * 0.9;
    x += Math.sin((a * Math.PI) / 180) * 120;
    y -= Math.cos((a * Math.PI) / 180) * 120;
    pts.push({x, y, a});
  }
  const stem = pts.map((p, i) => `${i ? 'L' : 'M'} ${p.x} ${p.y}`).join(' ');
  const bloom = ease((t - 0.4) / 3.2);
  const tip = pts[pts.length - 1];
  return (
    <AbsoluteFill style={{background: 'linear-gradient(#FDEBD0 0%, #F8C9A0 60%, #E9A58A 100%)'}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920">
        <circle cx={860} cy={520} r={110 + wave(t, 7) * 5} fill="#FFD27A" opacity={0.9} />
        {[0, 1, 2].map((i) => <ellipse key={i} cx={-200 + loop(t, 22 + i * 5, i * 0.3) * 1500} cy={470 + i * 120} rx={190} ry={44} fill="#fff" opacity={0.65} />)}
        <path d={stem} stroke="#3F7D4E" strokeWidth={22} strokeLinecap="round" strokeLinejoin="round" fill="none" />
        {pts.slice(1, 6).map((p, i) => {
          const s = i % 2 ? 1 : -1;
          const swing = wave(t, 3.4, i * 0.11) * 7 + s * 38;
          return (
            <g key={i} transform={`translate(${p.x} ${p.y}) rotate(${swing + p.a * 0.5})`}>
              <path d={`M 0 0 C ${s * 40} -50 ${s * 130} -40 ${s * 170} 10 C ${s * 120} 50 ${s * 40} 40 0 0 Z`} fill={i % 2 ? '#5FAF6E' : '#4A9A5D'} />
              <path d={`M 0 0 L ${s * 140} 6`} stroke="#2F6B3F" strokeWidth={4} />
            </g>
          );
        })}
        <g transform={`translate(${tip.x} ${tip.y}) rotate(${tip.a * 0.5 + wave(t, 9) * 3})`}>
          {Array.from({length: 8}, (_, i) => (
            <ellipse key={i} cx={0} cy={-70 * bloom} rx={26 * bloom} ry={62 * bloom} fill="#F25C78" transform={`rotate(${i * 45 + wave(t, 8, i * 0.05) * 3})`} />
          ))}
          <circle r={34 * bloom} fill="#FFD23F" />
        </g>
        <path d="M 440 1380 L 640 1380 L 610 1560 L 470 1560 Z" fill="#B5651D" />
        <rect x={430} y={1366} width={220} height={30} rx={10} fill="#9A5518" />
        {Array.from({length: 14}, (_, i) => {
          const k = loop(t, 6 + random(`pl${i}`) * 4, random(`ph${i}`));
          return <circle key={i} cx={180 + random(`px${i}`) * 720 + Math.sin(k * 6.28 + i) * 30} cy={1500 - k * 900} r={5 + random(`pr${i}`) * 5} fill="#FFF4B0" opacity={Math.sin(k * Math.PI) * 0.8} />;
        })}
      </svg>
    </AbsoluteFill>
  );
};

// ---------- 5. Remotion 3D (remotion-markup/3d.md): ThreeCanvas + lights, all driven by useCurrentFrame ----------
const Remotion3D: React.FC<{t: number}> = ({t}) => {
  const {width, height} = useVideoConfig();
  return (
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 40%, #243B6B 0%, #070B18 75%)'}}>
    <ThreeCanvas width={width} height={height} camera={{fov: 40, position: [0, 0.8, 14], near: 0.1, far: 40}} style={{position: 'absolute', inset: 0}}>
      <ambientLight intensity={0.35} />
      <directionalLight position={[5, 5, 5]} intensity={1.0} />
      <pointLight position={[Math.cos(t * 1.4) * 4, 2, Math.sin(t * 1.4) * 4 + 1]} intensity={80} color="#FF7AC8" />
      <pointLight position={[-Math.cos(t * 1.1) * 4, -1, 3]} intensity={60} color="#5BD0FF" />
      <mesh rotation={[t * 0.8, t * 1.1, 0]} position={[0, 0.3, 0]}>
        <boxGeometry args={[2, 2, 2]} />
        <meshStandardMaterial color="#C9D6FF" metalness={0.6} roughness={0.3} emissive="#2B3F8F" emissiveIntensity={0.35} />
      </mesh>
      <mesh rotation={[-t * 0.5, t * 0.7, 0]} position={[0, 0.3, 0]}>
        <icosahedronGeometry args={[2.1, 1]} />
        <meshBasicMaterial color="#FFE066" wireframe />
      </mesh>
      {[0, 1, 2].map((i) => {
        const a = t * 1.6 + (i * Math.PI * 2) / 3;
        return (
          <mesh key={i} position={[Math.cos(a) * 3.1, 0.3 + Math.sin(a * 2) * 0.5, Math.sin(a) * 3.1]}>
            <sphereGeometry args={[0.36, 32, 24]} />
            <meshStandardMaterial color={['#FF5D8F', '#5BD0FF', '#9BF06B'][i]} metalness={0.4} roughness={0.25} emissive={['#FF5D8F', '#5BD0FF', '#9BF06B'][i]} emissiveIntensity={0.25} />
          </mesh>
        );
      })}
      <mesh rotation={[Math.PI / 2.6, 0, t * 0.5]} position={[0, 0.3, 0]}>
        <torusGeometry args={[3.1, 0.03, 12, 120]} />
        <meshBasicMaterial color="#FFFFFF" transparent opacity={0.5} />
      </mesh>
    </ThreeCanvas>
  </AbsoluteFill>
  );
};

// ---------- 6. Lottie / transitions / light leaks / motion blur (Remotion) ----------
const kf = (frames: [number, number[]][]) => ({
  a: 1,
  k: frames.map(([t, s], i) => ({t, s, i: {x: [0.4], y: [1]}, o: {x: [0.6], y: [0]}, ...(i === frames.length - 1 ? {} : {})})),
});
const LOTTIE: any = {
  v: '5.7.0', fr: 30, ip: 0, op: 60, w: 600, h: 600, nm: 'itcodlab-test', ddd: 0, assets: [],
  layers: [
    {
      ddd: 0, ind: 1, ty: 4, nm: 'ball', sr: 1, ip: 0, op: 60, st: 0, bm: 0,
      ks: {o: {a: 0, k: 100}, r: {a: 0, k: 0}, p: kf([[0, [110, 420, 0]], [30, [490, 420, 0]], [60, [110, 420, 0]]]), a: {a: 0, k: [0, 0, 0]}, s: kf([[0, [100, 100, 100]], [15, [140, 70, 100]], [30, [100, 100, 100]], [45, [140, 70, 100]], [60, [100, 100, 100]]])},
      shapes: [{ty: 'gr', it: [{ty: 'el', p: {a: 0, k: [0, 0]}, s: {a: 0, k: [120, 120]}, d: 1}, {ty: 'fl', c: {a: 0, k: [1, 0.42, 0.2, 1]}, o: {a: 0, k: 100}, r: 1}, {ty: 'tr', p: {a: 0, k: [0, 0]}, a: {a: 0, k: [0, 0]}, s: {a: 0, k: [100, 100]}, r: {a: 0, k: 0}, o: {a: 0, k: 100}}]}],
    },
    {
      ddd: 0, ind: 2, ty: 4, nm: 'square', sr: 1, ip: 0, op: 60, st: 0, bm: 0,
      ks: {o: {a: 0, k: 100}, r: kf([[0, [0]], [60, [360]]]), p: {a: 0, k: [300, 200, 0]}, a: {a: 0, k: [0, 0, 0]}, s: {a: 0, k: [100, 100, 100]}},
      shapes: [{ty: 'gr', it: [{ty: 'rc', p: {a: 0, k: [0, 0]}, s: {a: 0, k: [130, 130]}, r: {a: 0, k: 24}, d: 1}, {ty: 'fl', c: {a: 0, k: [0.2, 0.7, 1, 1]}, o: {a: 0, k: 100}, r: 1}, {ty: 'tr', p: {a: 0, k: [0, 0]}, a: {a: 0, k: [0, 0]}, s: {a: 0, k: [100, 100]}, r: {a: 0, k: 0}, o: {a: 0, k: 100}}]}],
    },
  ],
};
const Card: React.FC<{c1: string; c2: string; label: string}> = ({c1, c2, label}) => (
  <AbsoluteFill style={{background: `linear-gradient(160deg, ${c1}, ${c2})`, alignItems: 'center', justifyContent: 'center', fontFamily: FONT, fontSize: 130, fontWeight: 900, color: '#fff'}}>{label}</AbsoluteFill>
);
const MovingBox: React.FC = () => {
  const f = useCurrentFrame();
  const x = ((f * 38) % (1080 + 400)) - 200;
  return <div style={{position: 'absolute', left: x, top: 780, width: 260, height: 260, borderRadius: 40, background: '#FF5D5D', boxShadow: '0 0 40px #FF5D5D'}} />;
};
const LightLeakBeat: React.FC<{n: number}> = ({n}) => {
  const f = useCurrentFrame();
  const width = 1080, height = 1920;
  return (
    <AbsoluteFill>
      <Card c1="#1B2A49" c2="#3E1F47" label="Light leak" />
      <Solid width={width} height={height} color="#000" effects={[lightLeak({seed: 3, hueShift: 0, progress: interpolate(f, [0, n - 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})]} style={{mixBlendMode: 'screen'}} />
    </AbsoluteFill>
  );
};
const Combo: React.FC<{t: number; n: number; beatLen: number; beatStatus: ('tested' | 'not_tested')[]}> = ({n, beatLen, beatStatus}) => {
  const width = 1080, height = 1920;
  const half = Math.round((beatLen + 12) / 2);
  const dur = (i: number) => (i === 3 ? n - 3 * beatLen : beatLen);
  return (
    <AbsoluteFill style={{background: '#101018'}}>
      <Sequence from={0} durationInFrames={beatLen}>
        <AbsoluteFill style={{background: '#FFF4D6', alignItems: 'center', justifyContent: 'center'}}>
          <Lottie animationData={LOTTIE} loop style={{width: 900, height: 900}} />
        </AbsoluteFill>
      </Sequence>
      <Sequence from={beatLen} durationInFrames={beatLen}>
        <TransitionSeries>
          <TransitionSeries.Sequence durationInFrames={half}><Card c1="#FF7A59" c2="#FFC145" label="Scene A" /></TransitionSeries.Sequence>
          <TransitionSeries.Transition presentation={slide({direction: 'from-right'})} timing={linearTiming({durationInFrames: 12})} />
          <TransitionSeries.Sequence durationInFrames={half}><Card c1="#2B6FED" c2="#8E7DFF" label="Scene B" /></TransitionSeries.Sequence>
        </TransitionSeries>
      </Sequence>
      <Sequence from={2 * beatLen} durationInFrames={beatLen}><LightLeakBeat n={beatLen} /></Sequence>
      <Sequence from={3 * beatLen} durationInFrames={dur(3)}>
        <AbsoluteFill style={{background: '#0E1424'}}>
          {beatStatus[3] === 'tested' ? (
            <HtmlInCanvasMotionBlur width={width} height={height} samples={10} shutterAngle={270}><MovingBox /></HtmlInCanvasMotionBlur>
          ) : <MovingBox />}
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};

// ---------- 7. viral-hooks-skill: the hook line (formula 019 "If you're still doing X, stop") ----------
const HookLine: React.FC<{t: number; text: string}> = ({t, text}) => {
  const {fps} = useVideoConfig();
  const words = text.split(' ');
  const last = words.length - 2;
  return (
    <AbsoluteFill style={{background: 'radial-gradient(circle at 50% 45%, #3B1D5A 0%, #0B0614 80%)'}}>
      <div style={{position: 'absolute', left: 70, right: 70, top: 560, textAlign: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 92, lineHeight: 1.18, color: '#fff'}}>
        {words.map((w, i) => {
          const s = spring({frame: Math.round((t - 0.3 - i * 0.32) * fps), fps, config: {damping: 10, stiffness: 140}});
          const hot = i >= last;
          const shake = hot && t > 0.3 + i * 0.32 + 0.2 ? Math.sin(t * 60 + i) * 4 : 0;
          return (
            <span key={i} style={{display: 'inline-block', margin: '0 12px', transform: `scale(${Math.max(0, s)}) translateX(${shake}px)`, color: hot ? '#FF3B30' : '#fff', textShadow: '0 4px 12px #000'}}>{w}</span>
          );
        })}
      </div>
      <div style={{position: 'absolute', left: 0, right: 0, top: 1220, textAlign: 'center', fontFamily: FONT, fontSize: 40, fontWeight: 800, color: '#FFE066', opacity: ease((t - 3.2) / 0.5)}}>
        formula 019: "agar aap ab bhi X kar rahe hain, to ruk jaiye"
      </div>
    </AbsoluteFill>
  );
};

export const SkillTest: React.FC<SkillTestProps> = (p) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames, width: cw} = useVideoConfig();
  const sc = cw / 1080;
  const Scaled: React.FC<{children: React.ReactNode}> = ({children}) => (
    <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920, transform: `scale(${sc})`, transformOrigin: '0 0'}}>{children}</div>
  );
  const t = frame / fps;
  const beatLen = Math.floor(durationInFrames / 4);
  const beat = p.part === 6 ? Math.min(3, Math.floor(frame / beatLen)) : undefined;
  let body: React.ReactNode = null;
  if (p.part === 1) body = <CartoonStreet t={t} />;
  else if (p.part === 2) body = <BlenderCard t={t} reason={p.reason ?? []} />;
  else if (p.part === 3) body = <Stickman t={t} />;
  else if (p.part === 4) body = <LivingPlant t={t} />;
  else if (p.part === 5) body = <Remotion3D t={t} />;
  else if (p.part === 6) body = <Combo t={t} n={durationInFrames} beatLen={beatLen} beatStatus={p.beat_status ?? ['tested', 'tested', 'tested', 'tested']} />;
  else if (p.part === 7) body = <HookLine t={t} text={p.hook ?? ''} />;
  const is3d = p.part === 1 || p.part === 5;
  return (
    <AbsoluteFill>
      {is3d ? body : <Scaled>{body}</Scaled>}
      <Scaled><Overlay {...p} t={t} beat={beat} /></Scaled>
    </AbsoluteFill>
  );
};
