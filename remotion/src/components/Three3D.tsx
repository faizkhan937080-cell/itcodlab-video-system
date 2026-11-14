// Real 3D scenes (three.js inside Remotion via @remotion/three). Every object is a 3D model that moves by itself:
// camera glides, steam and smoke are particle systems with their own motion, the ember flickers. Deterministic per frame.
import React, {useMemo} from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';

export type ThreeProps = {shot: 'cup_cig'; seed?: number};

const puffTexture = (() => {
  let tex: THREE.CanvasTexture | null = null;
  return () => {
    if (tex) return tex;
    const c = document.createElement('canvas');
    c.width = c.height = 128;
    const g = c.getContext('2d')!;
    const grd = g.createRadialGradient(64, 64, 2, 64, 64, 62);
    grd.addColorStop(0, 'rgba(255,255,255,0.9)');
    grd.addColorStop(0.45, 'rgba(255,255,255,0.35)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, 128, 128);
    tex = new THREE.CanvasTexture(c);
    return tex;
  };
})();

// one rising, swirling puff: position from age (seconds), all from seeded randoms
const Puff: React.FC<{i: number; t: number; origin: [number, number, number]; color: string; life: number; rise: number; seed: number; grow: number; sway: number}> = ({
  i, t, origin, color, life, rise, seed, grow, sway,
}) => {
  const phase = random(`${seed}-p-${i}`) * life;
  const age = ((t + phase) % life) / life; // 0..1
  const a = random(`${seed}-a-${i}`) * Math.PI * 2;
  const k = age;
  const x = origin[0] + Math.sin(a + k * 5.5) * sway * k + Math.sin(t * 0.9 + i) * 0.02;
  const z = origin[2] + Math.cos(a + k * 4.2) * sway * k;
  const y = origin[1] + k * rise;
  const s = 0.1 + k * grow;
  const op = Math.sin(Math.PI * Math.min(1, k * 1.15)) * 0.3;
  return (
    <sprite position={[x, y, z]} scale={[s, s, s]}>
      <spriteMaterial map={puffTexture()} color={color} transparent opacity={op} depthWrite={false} />
    </sprite>
  );
};

const cupProfile = (): THREE.Vector2[] => {
  const pts: [number, number][] = [[0, 0], [0.34, 0], [0.38, 0.02], [0.52, 0.18], [0.6, 0.42], [0.62, 0.62], [0.6, 0.64], [0.56, 0.62], [0.54, 0.6], [0.5, 0.2], [0.34, 0.07], [0, 0.07]];
  return pts.map(([x, y]) => new THREE.Vector2(x, y));
};
const saucerProfile = (): THREE.Vector2[] => [[0, 0], [0.5, 0], [0.95, 0.07], [1.0, 0.1], [0.96, 0.11], [0.5, 0.05], [0, 0.05]].map(([x, y]) => new THREE.Vector2(x, y));

export const Three3D: React.FC<ThreeProps> = ({seed = 3}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  const prog = frame / Math.max(1, durationInFrames - 1);
  const flick = 1 + Math.sin(t * 17) * 0.12 + Math.sin(t * 31) * 0.08;
  const cam: [number, number, number] = [-1.2 + prog * 2.0, 1.6 - prog * 0.3, 7.2 - prog * 1.4];
  const cup = useMemo(() => cupProfile(), []);
  const sau = useMemo(() => saucerProfile(), []);
  const ember: [number, number, number] = [1.44, 0.09, 0.9];
  return (
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 38%, #3a2a2c 0%, #140d10 70%)'}}>
      <ThreeCanvas width={width} height={height} camera={{fov: 38, position: cam, near: 0.1, far: 30}} style={{position: 'absolute', inset: 0}}>
        <Rig pos={cam} />
        <fog attach="fog" args={['#140d10', 5, 12]} />
        <ambientLight intensity={0.35} />
        <directionalLight position={[3, 5, 3]} intensity={1.7} color="#ffe2c4" />
        <directionalLight position={[-4, 2, -2]} intensity={0.9} color="#7aa0ff" />
        <pointLight position={ember} intensity={2.4 * flick} distance={3} color="#ff7a2a" />
        {/* table */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
          <planeGeometry args={[14, 14]} />
          <meshStandardMaterial color="#1b1214" roughness={0.35} metalness={0.2} />
        </mesh>
        {/* saucer + cup + tea */}
        <mesh position={[0, 0.005, 0]}><latheGeometry args={[sau, 64]} /><meshStandardMaterial color="#f2efe9" roughness={0.18} side={THREE.DoubleSide} /></mesh>
        <mesh position={[0, 0.1, 0]}><latheGeometry args={[cup, 64]} /><meshStandardMaterial color="#f6f3ee" roughness={0.16} side={THREE.DoubleSide} /></mesh>
        <mesh position={[0.62, 0.45, 0]} rotation={[0, 0, 0]}><torusGeometry args={[0.2, 0.045, 16, 40, Math.PI]} /><meshStandardMaterial color="#f6f3ee" roughness={0.16} /></mesh>
        <mesh position={[0, 0.66, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[0.55, 48]} /><meshStandardMaterial color="#b4561c" roughness={0.08} metalness={0.1} emissive="#3a1204" /></mesh>
        {/* cigarette lying on the table: paper, orange filter, glowing ember (axis along X, turned by yaw) */}
        <group position={[0.9, 0.05, 1.2]} rotation={[0, 0.5, 0]}>
          <mesh position={[0, 0, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.05, 0.05, 1.3, 20]} /><meshStandardMaterial color="#f4f1ea" roughness={0.7} /></mesh>
          <mesh position={[-0.8, 0, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.051, 0.051, 0.32, 20]} /><meshStandardMaterial color="#d58a3c" roughness={0.6} /></mesh>
          <mesh position={[0.66, 0, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.05, 0.043, 0.07, 20]} /><meshStandardMaterial color="#ff5a14" emissive="#ff4a00" emissiveIntensity={2.4 * flick} roughness={0.9} /></mesh>
        </group>
        {/* steam from the tea (white), smoke from the cigarette (grey-blue): real moving particles */}
        {Array.from({length: 110}).map((_, i) => <Puff key={`st${i}`} i={i} t={t} origin={[0, 0.68, 0]} color="#ffffff" life={4.2} rise={1.7} seed={seed} grow={0.6} sway={0.2} />)}
        {Array.from({length: 130}).map((_, i) => <Puff key={`sm${i}`} i={i + 100} t={t} origin={[1.46, 0.12, 0.9]} color="#aab2c0" life={4.5} rise={2.6} seed={seed} grow={0.7} sway={0.28} />)}
      </ThreeCanvas>
    </AbsoluteFill>
  );
};

// camera is moved every frame (a real 3D camera glide, not a zoom on a picture)
const Rig: React.FC<{pos: [number, number, number]}> = ({pos}) => {
  const {camera} = useThree();
  camera.position.set(pos[0], pos[1], pos[2]);
  camera.lookAt(0.8, 0.75, 0.5);
  camera.updateProjectionMatrix();
  return null;
};
