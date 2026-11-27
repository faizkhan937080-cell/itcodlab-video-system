// Real 3D marble objects for the health reel (three.js inside @remotion/three). Every object moves by itself
// (turntable, beating, swinging, falling sand, rising bubbles). Deterministic per frame: everything is a function of t.
import React, {useMemo} from 'react';
import {random} from 'remotion';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';

export type ObjName = 'bed' | 'five' | 'bust' | 'scalpel' | 'soap' | 'bars' | 'gavel' | 'hourglass' | 'globe' | 'capsule' | 'heart';

// ---------- materials ----------
let marbleTex: THREE.CanvasTexture | null = null;
const noise2 = (x: number, y: number, seed: number) => {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const r = (a: number, b: number) => {
    let h = (a * 374761393 + b * 668265263 + seed * 2147483647) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
  };
  const s = (t: number) => t * t * (3 - 2 * t);
  const a = r(xi, yi), b = r(xi + 1, yi), c = r(xi, yi + 1), d = r(xi + 1, yi + 1);
  return a + (b - a) * s(xf) + (c - a) * s(yf) + (a - b - c + d) * s(xf) * s(yf);
};
const fbm = (x: number, y: number, seed: number) => {
  let v = 0, amp = 0.5, f = 1;
  for (let o = 0; o < 5; o++) { v += amp * noise2(x * f, y * f, seed + o); amp *= 0.5; f *= 2.03; }
  return v;
};
const getMarbleTex = () => {
  if (marbleTex) return marbleTex;
  const N = 384;
  const c = document.createElement('canvas');
  c.width = c.height = N;
  const g = c.getContext('2d')!;
  const img = g.createImageData(N, N);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const u = x / N * 4, v = y / N * 4;
      const w = fbm(u, v, 3);
      const vein = Math.abs(Math.sin((u * 1.3 + v * 0.7 + w * 3.2) * Math.PI));
      const thin = Math.pow(1 - vein, 14);                // thin dark veins
      const cloud = fbm(u * 2, v * 2, 11) * 0.10;         // soft grey clouds
      const speck = noise2(x * 3.1, y * 3.1, 77) > 0.93 ? 0.07 : 0;
      const k = 0.74 - cloud * 1.6 - thin * 0.5 - speck;
      const i = (y * N + x) * 4;
      img.data[i] = 238 * k + 4; img.data[i + 1] = 233 * k + 4; img.data[i + 2] = 230 * k + 4; img.data[i + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  marbleTex = new THREE.CanvasTexture(c);
  marbleTex.wrapS = marbleTex.wrapT = THREE.RepeatWrapping;
  marbleTex.colorSpace = THREE.SRGBColorSpace;
  return marbleTex;
};

export const useMats = () =>
  useMemo(() => {
    const t = getMarbleTex();
    const marble = new THREE.MeshPhysicalMaterial({map: t, roughness: 0.32, metalness: 0, clearcoat: 0.35, clearcoatRoughness: 0.25, envMapIntensity: 0.55});
    const satin = new THREE.MeshPhysicalMaterial({color: '#B8324F', roughness: 0.38, metalness: 0, sheen: 1, sheenRoughness: 0.35, sheenColor: new THREE.Color('#ff9bb0'), clearcoat: 0.25, envMapIntensity: 1.1});
    const blush = new THREE.MeshPhysicalMaterial({map: t, color: '#e8aeba', roughness: 0.3, clearcoat: 0.4, clearcoatRoughness: 0.2, envMapIntensity: 0.9});
    const dark = new THREE.MeshPhysicalMaterial({color: '#3a1d27', roughness: 0.4, clearcoat: 0.3, envMapIntensity: 0.8});
    const glass = new THREE.MeshPhysicalMaterial({color: '#ffffff', roughness: 0.05, metalness: 0, transparent: true, opacity: 0.28, clearcoat: 1, envMapIntensity: 1.4, side: THREE.DoubleSide, depthWrite: false});
    const bubble = new THREE.MeshPhysicalMaterial({color: '#ffe3ea', roughness: 0.06, metalness: 0.15, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 2.4, iridescence: 0.6});
    return {marble, satin, blush, dark, glass, bubble};
  }, []);
type Mats = ReturnType<typeof useMats>;

/** soft studio reflections (RoomEnvironment) so stone and satin look real */
export const Studio: React.FC = () => {
  const {gl, scene} = useThree();
  useMemo(() => {
    const pm = new THREE.PMREMGenerator(gl);
    scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    pm.dispose();
  }, [gl, scene]);
  return (
    <>
      <ambientLight intensity={0.12} color="#ffeef0" />
      <directionalLight position={[-3, 4.5, 4]} intensity={1.5} color="#fff1e3" />
      <directionalLight position={[4, 1.5, 2]} intensity={0.55} color="#f2b9c6" />
      <directionalLight position={[0, 2, -4]} intensity={0.5} color="#ffffff" />
    </>
  );
};

const ease = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
const back = (x: number) => {
  const c1 = 1.5, c3 = c1 + 1, k = Math.min(1, Math.max(0, x));
  return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2);
};
const lathe = (pts: [number, number][], seg = 56) => new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), seg);

// ---------- objects ----------
const Bed: React.FC<{t: number; m: Mats}> = ({m}) => {
  const frame = useMemo(() => new RoundedBoxGeometry(2.1, 0.14, 1.15, 4, 0.05), []);
  const mat = useMemo(() => new RoundedBoxGeometry(1.95, 0.26, 1.0, 5, 0.12), []);
  const pil = useMemo(() => new RoundedBoxGeometry(0.55, 0.2, 0.78, 6, 0.1), []);
  const head = useMemo(() => new RoundedBoxGeometry(0.1, 0.85, 1.15, 4, 0.04), []);
  const blk = useMemo(() => new RoundedBoxGeometry(1.15, 0.1, 1.04, 5, 0.05), []);
  return (
    <group position={[0, -0.35, 0]}>
      <mesh geometry={frame} position={[0, 0.3, 0]} material={m.marble} />
      {[[-0.95, -0.5], [-0.95, 0.5], [0.95, -0.5], [0.95, 0.5]].map(([x, z], i) => (
        <mesh key={i} position={[x, 0.12, z]} material={m.marble}><cylinderGeometry args={[0.06, 0.05, 0.3, 24]} /></mesh>
      ))}
      <mesh geometry={mat} position={[0, 0.5, 0]} material={m.marble} />
      <mesh geometry={pil} position={[-0.68, 0.74, 0]} rotation={[0, 0, 0.08]} material={m.blush} />
      <mesh geometry={head} position={[-1.02, 0.7, 0]} material={m.marble} />
      <mesh geometry={blk} position={[0.35, 0.69, 0]} material={m.satin} />
    </group>
  );
};

const Five: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  const body = useMemo(() => lathe([[0, 0], [0.26, 0], [0.27, 0.03], [0.2, 0.3], [0.1, 0.62], [0.09, 0.7], [0.0, 0.7]]), []);
  return (
    <group position={[0, -0.35, 0]}>
      {[0, 1, 2, 3, 4].map((i) => {
        const dt = t - 0.1 - i * 0.14;
        const s = dt < 0 ? 0.001 : Math.max(0.001, back(dt / 0.35));
        const last = i === 4;
        const mix = last ? ease((t - 1.1) / 0.5) : 0;
        const mt = mix > 0.5 ? m.satin : m.marble;
        return (
          <group key={i} position={[(i - 2) * 0.46, 0, 0]} scale={[s, s * 1.3, s]} rotation={[0, Math.sin(t * 1.3 + i) * 0.25, 0]}>
            <mesh geometry={body} material={mt} />
            <mesh position={[0, 0.88, 0]} material={mt}><sphereGeometry args={[0.2, 40, 28]} /></mesh>
          </group>
        );
      })}
    </group>
  );
};

const Bust: React.FC<{t: number; m: Mats}> = ({m}) => {
  const shoulders = useMemo(() => lathe([[0, -1.0], [1.0, -1.0], [1.05, -0.9], [0.95, -0.62], [0.7, -0.4], [0.36, -0.28], [0.2, -0.15], [0.19, 0.2], [0, 0.2]]), []);
  const scaleX = 1.0;
  const tube = useMemo(() => new THREE.TubeGeometry(new THREE.CatmullRomCurve3([
    new THREE.Vector3(-0.28, -0.3, 0.1), new THREE.Vector3(-0.42, -0.5, 0.3), new THREE.Vector3(-0.24, -0.72, 0.46),
    new THREE.Vector3(0, -0.8, 0.5), new THREE.Vector3(0.24, -0.72, 0.46), new THREE.Vector3(0.42, -0.5, 0.3), new THREE.Vector3(0.28, -0.3, 0.1)]), 64, 0.04, 12), []);
  return (
    <group position={[0, -0.05, 0]} scale={[scaleX * 0.95, 0.95, 0.95]}>
      <mesh geometry={shoulders} material={m.marble} scale={[1.15, 1, 0.7]} />
      <mesh position={[0, 0.62, 0.02]} scale={[0.4, 0.55, 0.45]} material={m.marble}><sphereGeometry args={[1, 96, 72]} /></mesh>
      <mesh position={[0, 0.3, 0.16]} scale={[0.24, 0.22, 0.24]} material={m.marble}><sphereGeometry args={[1, 64, 48]} /></mesh>
      <mesh position={[0, 0.52, 0.43]} rotation={[0.2, 0, 0]} scale={[1, 1.1, 0.8]} material={m.marble}><coneGeometry args={[0.06, 0.24, 32]} /></mesh>
      <mesh position={[0, 0.66, 0.42]} scale={[0.3, 0.05, 0.1]} material={m.marble}><sphereGeometry args={[1, 32, 20]} /></mesh>
      {/* pink surgeon cap */}
      <mesh position={[0, 0.78, -0.03]} scale={[0.43, 0.4, 0.47]} material={m.satin}><sphereGeometry args={[1, 48, 32, 0, Math.PI * 2, 0, Math.PI * 0.5]} /></mesh>
      {/* stethoscope */}
      <mesh geometry={tube} material={m.satin} position={[0, 0, 0]} scale={[1.1, 1, 1]} />
      <mesh position={[0, -0.82, 0.52]} rotation={[Math.PI / 2, 0, 0]} material={m.dark}><cylinderGeometry args={[0.11, 0.11, 0.06, 32]} /></mesh>
    </group>
  );
};

const Scalpel: React.FC<{t: number; m: Mats}> = ({m}) => {
  const blade = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(0, 0.12); s.lineTo(0.9, 0.1); s.quadraticCurveTo(1.25, 0.0, 1.5, -0.12); s.lineTo(0.9, -0.1); s.lineTo(0, -0.12); s.closePath();
    return new THREE.ExtrudeGeometry(s, {depth: 0.03, bevelEnabled: true, bevelSize: 0.012, bevelThickness: 0.012, bevelSegments: 3});
  }, []);
  return (
    <group position={[0, 0, 0]}>
     <mesh position={[0, -0.78, 0]} material={m.marble}><boxGeometry args={[2.7, 0.14, 1.0]} /></mesh>
     <group position={[0.2, -0.58, 0]}>
      <mesh rotation={[0, 0, Math.PI / 2]} position={[-0.45, 0, 0]} material={m.marble}><cylinderGeometry args={[0.1, 0.13, 1.7, 40]} /></mesh>
      <mesh rotation={[0, 0, Math.PI / 2]} position={[0.45, 0, 0]} material={m.satin}><cylinderGeometry args={[0.07, 0.1, 0.22, 40]} /></mesh>
      <mesh geometry={blade} position={[0.5, 0, -0.015]} material={m.marble} />
     </group>
    </group>
  );
};

const Bubbles: React.FC<{t: number; m: Mats; n: number; seed: number}> = ({t, m, n, seed}) => (
  <>
    {Array.from({length: n}).map((_, i) => {
      const life = 2.2 + random(`${seed}-l${i}`) * 1.2;
      const ph = random(`${seed}-p${i}`) * life;
      const k = ((t + ph) % life) / life;
      const x = (random(`${seed}-x${i}`) - 0.5) * 1.7 + Math.sin(t * 2.2 + i * 1.7) * 0.12 * k;
      const z = (random(`${seed}-z${i}`) - 0.5) * 0.7;
      const r = 0.14 + random(`${seed}-r${i}`) * 0.16;
      const grow = Math.min(1, k * 5);
      const pop = k > 0.9 ? 1 + (k - 0.9) * 4 : 1;     // swells just before it pops
      const gone = k > 0.96 ? 0.001 : 1;
      return (
        <mesh key={i} position={[x, 0.55 + k * 1.6, z]} scale={Math.max(0.001, r * grow * pop * gone)} material={m.bubble}>
          <sphereGeometry args={[1, 40, 28]} />
        </mesh>
      );
    })}
  </>
);

const Soap: React.FC<{t: number; m: Mats; pink?: boolean}> = ({t, m, pink}) => {
  const g = useMemo(() => new RoundedBoxGeometry(1.45, 0.5, 0.9, 8, 0.2), []);
  return (
    <group position={[0, -0.7, 0]}>
      <mesh geometry={g} position={[0, 0.25, 0]} material={pink ? m.blush : m.marble} />
      <mesh position={[0, 0.5, 0]} scale={[0.6, 0.04, 0.34]} material={m.satin}><sphereGeometry args={[1, 32, 16]} /></mesh>
      <Bubbles t={t} m={m} n={pink ? 8 : 9} seed={pink ? 9 : 4} />
    </group>
  );
};

const Bars: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  const go = ease((t - 0.7) / 1.0);
  const hL = 2.0 - (2.0 - 0.22) * go;
  const grow = (d: number) => Math.max(0.001, back((t - d) / 0.4));
  const base = useMemo(() => new RoundedBoxGeometry(2.2, 0.16, 1.0, 4, 0.06), []);
  return (
    <group position={[0, -0.95, 0]}>
      <mesh geometry={base} position={[0, 0.08, 0]} material={m.marble} />
      <group position={[-0.5, 0.16, 0]} scale={[1, grow(0.1), 1]}>
        <mesh position={[0, hL / 2, 0]} material={m.satin}><boxGeometry args={[0.62, hL, 0.62]} /></mesh>
      </group>
      <group position={[0.55, 0.16, 0]} scale={[1, grow(0.3), 1]}>
        <mesh position={[0, 0.11, 0]} material={m.marble}><boxGeometry args={[0.62, 0.22, 0.62]} /></mesh>
      </group>
    </group>
  );
};

const Gavel: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  // The head is a cylinder whose AXIS is the strike direction (local y), the handle enters its side at the centre (like a real mallet).
  // Hinge at the hand (PX,PY), handle length L. Lowest point of the head = c_y - HL*cos(a) - R*|sin(a)|.
  // PY is solved so that at A_HIT that lowest point == PAD_TOP (touching, never inside).
  const L = 1.5, R = 0.3, HL = 0.45, PAD_TOP = 0.24, A_HIT = -0.5, A_UP = 0.15, PX = -1.12;
  const low = (py: number, a: number) => py + L * Math.sin(a) - HL * Math.cos(a) - R * Math.abs(Math.sin(a));
  const PY = PAD_TOP - (L * Math.sin(A_HIT) - HL * Math.cos(A_HIT) - R * Math.abs(Math.sin(A_HIT)));
  const cyc = (t % 1.3) / 1.3;
  let a: number;
  if (cyc < 0.5) a = A_HIT + (A_UP - A_HIT) * ease(cyc / 0.5);                           // lift
  else if (cyc < 0.62) a = A_UP + (A_HIT - A_UP) * Math.pow((cyc - 0.5) / 0.12, 2.2);    // fast strike
  else if (cyc < 0.72) a = A_HIT + 0.16 * Math.sin(((cyc - 0.62) / 0.1) * Math.PI);       // small bounce, stays above the pad
  else a = A_HIT;
  a = Math.max(A_HIT, a);
  const guard = Math.max(0, PAD_TOP - low(PY, a));
  return (
    <group position={[0, -0.75, 0]}>
      <mesh position={[0.2, 0.06, 0]} material={m.marble}><cylinderGeometry args={[0.95, 1.05, 0.12, 64]} /></mesh>
      <mesh position={[0.2, 0.18, 0]} material={m.satin}><cylinderGeometry args={[0.55, 0.6, 0.12, 48]} /></mesh>
      <group position={[PX, PY + guard, 0]} rotation={[0, 0, a]}>
        <mesh position={[L / 2, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={m.marble}><cylinderGeometry args={[0.07, 0.09, L, 32]} /></mesh>
        <group position={[L, 0, 0]}>
          <mesh material={m.marble}><cylinderGeometry args={[R, R, HL * 2, 48]} /></mesh>
          <mesh position={[0, HL - 0.05, 0]} material={m.satin}><cylinderGeometry args={[R + 0.015, R + 0.015, 0.1, 48]} /></mesh>
          <mesh position={[0, -HL + 0.05, 0]} material={m.satin}><cylinderGeometry args={[R + 0.015, R + 0.015, 0.1, 48]} /></mesh>
        </group>
      </group>
    </group>
  );
};

const Hourglass: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  const cone = useMemo(() => lathe([[0.0, 0], [0.55, 0.0], [0.5, 0.2], [0.4, 0.55], [0.08, 0.85], [0.06, 0.95]], 48), []);
  const prog = Math.min(1, Math.max(0, (t - 0.4) / 2.2));
  const topH = 0.62 * (1 - prog) + 0.02, botH = 0.62 * prog + 0.02;
  return (
    <group position={[0, -0.1, 0]} scale={0.95}>
      <mesh position={[0, 0.98, 0]} material={m.marble}><cylinderGeometry args={[0.78, 0.8, 0.12, 64]} /></mesh>
      <mesh position={[0, -0.98, 0]} material={m.marble}><cylinderGeometry args={[0.8, 0.78, 0.12, 64]} /></mesh>
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[Math.cos(i * 2.094 + 0.5) * 0.7, 0, Math.sin(i * 2.094 + 0.5) * 0.7]} material={m.marble}><cylinderGeometry args={[0.035, 0.035, 1.9, 16]} /></mesh>
      ))}
      <group position={[0, 0.92, 0]} rotation={[Math.PI, 0, 0]}><mesh geometry={cone} material={m.glass} /></group>
      <group position={[0, -0.92, 0]}><mesh geometry={cone} material={m.glass} /></group>
      <mesh position={[0, 0.1 + topH * 0.35, 0]} scale={[0.3 * (0.5 + 0.5 * (1 - prog)), topH * 0.55, 0.3 * (0.5 + 0.5 * (1 - prog))]} material={m.blush}><sphereGeometry args={[1, 32, 20, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2]} /></mesh>
      <mesh position={[0, -0.9 + botH * 0.35, 0]} scale={[0.5, botH * 0.7, 0.5]} material={m.blush}><sphereGeometry args={[1, 32, 20, 0, Math.PI * 2, 0, Math.PI / 2]} /></mesh>
      {prog < 1 ? <mesh position={[0, -0.4, 0]} material={m.blush}><cylinderGeometry args={[0.012, 0.012, 1.0, 8]} /></mesh> : null}
    </group>
  );
};

const Globe: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  const stand = useMemo(() => lathe([[0, -1.1], [0.55, -1.1], [0.6, -1.05], [0.2, -0.95], [0.12, -0.7], [0, -0.7]]), []);
  return (
    <group position={[0, 0, 0]} scale={0.92}>
      <mesh geometry={stand} material={m.marble} />
      <group rotation={[0, 0, 0.41]}>
        <mesh rotation={[Math.PI / 2, 0, 0]} material={m.satin}><torusGeometry args={[1.02, 0.035, 20, 96]} /></mesh>
        <group rotation={[0, t * 0.9, 0]}>
          <mesh material={m.marble}><sphereGeometry args={[0.82, 64, 48]} /></mesh>
          <mesh rotation={[Math.PI / 2, 0, 0]} material={m.blush}><torusGeometry args={[0.822, 0.012, 8, 96]} /></mesh>
          {[0, 1, 2].map((i) => (
            <mesh key={i} rotation={[0, (i * Math.PI) / 3, 0]} material={m.blush}><torusGeometry args={[0.822, 0.01, 8, 96]} /></mesh>
          ))}
          {[-0.45, 0.45].map((y) => (
            <mesh key={y} position={[0, y, 0]} rotation={[Math.PI / 2, 0, 0]} material={m.blush}><torusGeometry args={[Math.sqrt(0.82 * 0.82 - y * y) + 0.002, 0.01, 8, 96]} /></mesh>
          ))}
        </group>
      </group>
    </group>
  );
};

const Capsule: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  const half = useMemo(() => lathe([[0, 0], [0.42, 0], [0.42, 0.55], [0.4, 0.7], [0.3, 0.88], [0.16, 0.99], [0, 1.03]], 56), []);
  const gap = 0.05 + 0.55 * Math.max(0, Math.sin(Math.max(0, t - 0.5) * 1.6)) ** 2;
  return (
    <group rotation={[0, 0, 0.6]} position={[0, 0, 0]}>
      <group position={[0, gap, 0]}><mesh geometry={half} material={m.marble} /></group>
      <group position={[0, -gap, 0]} rotation={[Math.PI, 0, 0]}><mesh geometry={half} material={m.satin} /></group>
    </group>
  );
};

const Heart: React.FC<{t: number; m: Mats}> = ({t, m}) => {
  const g = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(0, -0.95);
    s.bezierCurveTo(-0.2, -0.75, -1.05, -0.2, -1.0, 0.35);
    s.bezierCurveTo(-0.98, 0.9, -0.3, 1.0, 0, 0.55);
    s.bezierCurveTo(0.3, 1.0, 0.98, 0.9, 1.0, 0.35);
    s.bezierCurveTo(1.05, -0.2, 0.2, -0.75, 0, -0.95);
    const e = new THREE.ExtrudeGeometry(s, {depth: 0.35, bevelEnabled: true, bevelSegments: 12, bevelSize: 0.1, bevelThickness: 0.14, curveSegments: 64});
    e.center();
    return e;
  }, []);
  const ph = (t * 1.25) % 1;
  const beat = 1 + 0.09 * Math.exp(-Math.pow((ph - 0.08) * 9, 2)) + 0.06 * Math.exp(-Math.pow((ph - 0.32) * 9, 2));
  return (
    <group scale={0.95 * beat} rotation={[0, 0, 0.0]}>
      <mesh geometry={g} material={m.satin} />
    </group>
  );
};

export const OBJ: Record<ObjName, React.FC<{t: number; m: Mats}>> = {
  bed: Bed, five: Five, bust: Bust, scalpel: Scalpel, soap: Soap, bars: Bars, gavel: Gavel, hourglass: Hourglass, globe: Globe, capsule: Capsule, heart: Heart,
};
export const SoapPink: React.FC<{t: number; m: Mats}> = (p) => <Soap {...p} pink />;

/** per-object presentation: how it is turned and tilted toward the camera, and its pop-in */
export const POSE: Record<ObjName, {yaw: number; sway: number; spin: number; tilt: number; scale: number}> = {
  bed: {yaw: -0.6, sway: 0.35, spin: 0, tilt: 0.38, scale: 1.0},
  five: {yaw: 0, sway: 0.0, spin: 0, tilt: 0.12, scale: 1.0},
  bust: {yaw: -0.1, sway: 0.4, spin: 0, tilt: 0.04, scale: 1.0},
  scalpel: {yaw: 0.0, sway: 0.45, spin: 0, tilt: 0.5, scale: 1.0},
  soap: {yaw: -0.3, sway: 0.4, spin: 0, tilt: 0.3, scale: 1.0},
  bars: {yaw: -0.35, sway: 0.25, spin: 0, tilt: 0.22, scale: 1.0},
  gavel: {yaw: -0.4, sway: 0.2, spin: 0, tilt: 0.28, scale: 0.8},
  hourglass: {yaw: 0, sway: 0, spin: 0.7, tilt: 0.1, scale: 1.0},
  globe: {yaw: 0, sway: 0.15, spin: 0, tilt: 0.12, scale: 1.0},
  capsule: {yaw: 0, sway: 0, spin: 0.8, tilt: 0.1, scale: 1.0},
  heart: {yaw: 0, sway: 0.55, spin: 0, tilt: 0.0, scale: 1.0},
};
