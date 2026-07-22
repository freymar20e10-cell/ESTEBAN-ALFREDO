/**
 * ParticleSystem — el organismo de partículas.
 * Un solo BufferGeometry creado UNA vez; a partir de ahí, la CPU solo mueve
 * números (uniforms). El movimiento, morphing, ondas, remolino e interacción
 * ocurren íntegramente en el vertex shader.
 */
import { useFrame, useThree } from "@react-three/fiber";
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef } from "react";
import * as THREE from "three";
import type { CoreConfig } from "../config/CoreConfig";
import type { CoreStateName } from "../config/CoreState";
import { AnimationManager } from "./AnimationManager";
import { InteractionEngine } from "./InteractionEngine";
import { MorphEngine } from "./MorphEngine";
import type { ShapeContext } from "./ShapeRegistry";
import { VERTEX_SHADER, FRAGMENT_SHADER } from "./shaders";

export interface ParticleSystemHandle {
  setShape(name: string, ctx?: Partial<ShapeContext>): Promise<void>;
  setState(name: CoreStateName): void;
  setAudioLevel(v: number): void;
  getShape(): string;
  getState(): CoreStateName;
}

interface Props {
  config: CoreConfig;
  initialPositions: Float32Array;
  /** Se dispara cuando el sistema ya puede recibir órdenes (morph/estado). */
  onReady?: () => void;
}

export const ParticleSystem = forwardRef<ParticleSystemHandle, Props>(function ParticleSystem(
  { config, initialPositions, onReady },
  ref,
) {
  const { camera, gl, clock } = useThree();
  const pivotRef = useRef<THREE.Group>(null!);
  const configRef = useRef(config);
  configRef.current = config;

  const { geometry, material, morph, anim, interaction } = useMemo(() => {
    const n = config.particleCount;
    const geometry = new THREE.BufferGeometry();
    // 'position' es requerido por three aunque el shader use aFrom/aTo
    geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
    const seeds = new Float32Array(n);
    const sizes = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      seeds[i] = Math.random();
      sizes[i] = 0.7 + Math.pow(Math.random(), 2.2) * 2.6;
    }
    geometry.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    geometry.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
    geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), config.coreRadius * 6);

    const morph = new MorphEngine(geometry, n, initialPositions, config.shape);
    const anim = new AnimationManager(config);
    const interaction = new InteractionEngine();

    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uMorph: { value: 1 },
        uStagger: { value: config.morphStagger },
        uPixelRatio: { value: 1 },
        uSize: { value: config.particleSize },
        uScale: { value: 1 },
        uSpeed: { value: 1 },
        uNoiseScale: { value: config.noiseScale },
        uNoiseStrength: { value: config.noiseStrength },
        uEnergy: { value: 0.2 },
        uWave: { value: 0 },
        uAudio: { value: 0 },
        uExpand: { value: 0 },
        uJitter: { value: 0 },
        uVortex: { value: 0 },
        uMouse: { value: new THREE.Vector3(999, 999, 999) },
        uMouseStrength: { value: config.mouseInfluence },
        uClickT: { value: -10 },
        uColor: { value: new THREE.Color(config.color) },
        uColorHot: { value: new THREE.Color(config.hotColor) },
        uGlow: { value: config.glow },
        uCoreRadius: { value: config.coreRadius },
        uOpacity: { value: config.opacity },
        uDim: { value: 1 },
      },
    });
    return { geometry, material, morph, anim, interaction };
    // se crea una sola vez a propósito: los buffers viven toda la sesión
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const detach = interaction.attach(gl.domElement, camera, () => clock.getElapsedTime());
    onReady?.();
    return () => { detach(); geometry.dispose(); material.dispose(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useImperativeHandle(ref, () => ({
    async setShape(name, ctx) {
      await morph.setShape(name, {
        radius: configRef.current.coreRadius,
        text: ctx?.text,
        svg: ctx?.svg,
        url: ctx?.url,
      });
    },
    setState(name) { anim.setState(name); },
    setAudioLevel(v) { anim.setAudioLevel(v); },
    getShape() { return morph.currentShape; },
    getState() { return anim.state; },
  }), [morph, anim]);

  useFrame((_, delta) => {
    const cfg = configRef.current;
    // pause(): congela la simulación (los uniforms no avanzan) pero el
    // post-procesado sigue renderizando el último fotograma estable.
    if (cfg.paused) return;
    const t = clock.getElapsedTime();
    const u = material.uniforms;
    anim.setConfig(cfg);
    anim.update(Math.min(delta, 0.1), morph.currentShape === "blackhole" ? 1 : 0);

    u.uTime.value = t;
    u.uMorph.value = morph.update(Math.min(delta, 0.1), cfg.transitionSpeed);
    u.uStagger.value = cfg.morphStagger;
    u.uPixelRatio.value = Math.min(gl.getPixelRatio(), cfg.maxPixelRatio);
    u.uSize.value = cfg.particleSize;
    u.uScale.value = anim.breathScale(t) * (cfg.coreRadius / 2.1);
    u.uSpeed.value = anim.live.speed;
    u.uNoiseScale.value = cfg.noiseScale;
    u.uNoiseStrength.value = anim.live.noiseStrength;
    u.uEnergy.value = anim.live.energy;
    u.uWave.value = anim.live.wave;
    u.uAudio.value = anim.live.audio;
    u.uExpand.value = anim.live.expand;
    u.uJitter.value = anim.live.jitter;
    u.uVortex.value = anim.live.vortex;
    u.uMouse.value.copy(interaction.mouseWorld);
    u.uMouseStrength.value = cfg.mouseInfluence;
    u.uClickT.value = interaction.clickTime;
    (u.uColor.value as THREE.Color).copy(anim.live.color);
    u.uGlow.value = cfg.glow;
    u.uOpacity.value = cfg.opacity;
    u.uDim.value = anim.live.dim;

    interaction.update(pivotRef.current, cfg.rotationSpeed, anim.live.energy);
  });

  return (
    <group ref={pivotRef}>
      <points geometry={geometry} material={material} frustumCulled={false} />
      <GlowCore anim={anim} morph={morph} config={configRef} />
    </group>
  );
});

/** Brillo central por capas + oscurecimiento del horizonte en modo agujero negro. */
function GlowCore({ anim, morph, config }: {
  anim: AnimationManager;
  morph: MorphEngine;
  config: React.MutableRefObject<CoreConfig>;
}) {
  const { hot, mid, far, horizon } = useMemo(() => {
    const make = (stops: [number, string][]) => {
      const c = document.createElement("canvas");
      c.width = c.height = 128;
      const x = c.getContext("2d")!;
      const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
      stops.forEach(([o, col]) => g.addColorStop(o, col));
      x.fillStyle = g; x.fillRect(0, 0, 128, 128);
      const t = new THREE.CanvasTexture(c);
      return t;
    };
    const glowTex = make([[0, "rgba(255,255,255,1)"], [0.25, "rgba(255,255,255,.5)"], [0.6, "rgba(255,255,255,.12)"], [1, "rgba(255,255,255,0)"]]);
    const sprite = (scale: number, opacity: number, color: string) => {
      const m = new THREE.SpriteMaterial({ map: glowTex, transparent: true, opacity, color, blending: THREE.AdditiveBlending, depthWrite: false });
      const s = new THREE.Sprite(m); s.scale.setScalar(scale); return s;
    };
    const horizonMat = new THREE.MeshBasicMaterial({ color: "#000206", transparent: true, opacity: 0 });
    const horizon = new THREE.Mesh(new THREE.SphereGeometry(0.7, 32, 32), horizonMat);
    // Resplandor central discreto: una brasa, no un foco. Las partículas
    // calientes del centro ya aportan la mayor parte de la luz.
    return { hot: sprite(0.46, 0.5, "#ffffff"), mid: sprite(1.35, 0.28, "#56d9ff"), far: sprite(3.4, 0.09, "#2fa8e6"), horizon };
  }, []);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const l = anim.live;
    const cfg = config.current;
    const bh = morph.currentShape === "blackhole" ? l.vortex : 0;
    const g = (0.85 + Math.sin(t * l.pulseSpeed * 1.25) * 0.1 + l.energy * 0.15) * l.dim * cfg.glow;

    (hot.material as THREE.SpriteMaterial).opacity = 0.34 * g * (1 - bh * 0.8);
    (mid.material as THREE.SpriteMaterial).opacity = 0.2 * g;
    (mid.material as THREE.SpriteMaterial).color.copy(l.color).lerp(new THREE.Color("#ffffff"), 0.25);
    (far.material as THREE.SpriteMaterial).opacity = (0.06 + l.energy * 0.04) * l.dim;
    (far.material as THREE.SpriteMaterial).color.copy(l.color);
    hot.scale.setScalar((0.44 + Math.sin(t * l.pulseSpeed) * 0.04 + l.energy * 0.12) * (1 - bh * 0.45));
    mid.scale.setScalar(1.3 + Math.sin(t * l.pulseSpeed * 0.8) * 0.12 + bh * 0.5);

    // horizonte de eventos: aparece solo en modo agujero negro
    (horizon.material as THREE.MeshBasicMaterial).opacity = bh * 0.96;
    horizon.scale.setScalar(0.9 + bh * 0.15);
  });

  return (
    <>
      <primitive object={hot} />
      <primitive object={mid} />
      <primitive object={far} />
      <primitive object={horizon} />
    </>
  );
}
