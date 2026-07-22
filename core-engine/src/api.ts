/**
 * API pública del motor. Uso desde cualquier página:
 *
 *   const core = JarvisCoreEngine.mount(document.getElementById('nucleo'), {
 *     particleCount: 12000, color: '#37d8ff',
 *   });
 *   core.setShape('galaxy');
 *   core.setShape('text', { text: 'JARVIS' });
 *   core.setState('pensando');
 *   core.setAudioLevel(0.6);       // mientras habla
 *   core.registerShape('miForma', (n, { radius }) => new Float32Array(n*3));
 */
import { createElement, createRef } from "react";
import { createRoot, type Root } from "react-dom/client";
import { mergeConfig, type CoreConfig } from "./config/CoreConfig";
import { CORE_STATES, isCoreState, type CoreStateName } from "./config/CoreState";
import { CoreEngine, type CoreEngineHandle } from "./CoreEngine";
import { generateShape, listShapes, registerShape, registerAsyncShape, type ShapeContext, type ShapeGenerator } from "./engine/ShapeRegistry";

export interface JarvisCoreHandle {
  setShape(name: string, ctx?: Partial<ShapeContext>): Promise<void>;
  setState(name: string): void;
  setAudioLevel(level: number): void;
  /** Color base del núcleo (hex). Los estados con color propio lo tiñen temporalmente. */
  setColor(hex: string): void;
  /** Energía extra 0..1 (sube brillo, rotación y turbulencia). */
  setEnergy(v: number): void;
  /** Brillo de las partículas 0..~1.5. */
  setGlow(v: number): void;
  /** Intensidad del bloom (resplandor). 0 = apagado. */
  setBloom(v: number): void;
  /** Umbral del bloom 0..1: cuánto tiene que brillar algo para florecer. */
  setBloomThreshold(v: number): void;
  /** Fuerza del ruido/turbulencia orgánica. */
  setNoiseIntensity(v: number): void;
  /** Velocidad de las transiciones de forma/estado (1 ≈ 1s). */
  setMorphSpeed(v: number): void;
  /** Rotación automática del núcleo (rad/seg aprox). */
  setRotation(v: number): void;
  /** Radio/escala del núcleo en unidades de mundo. */
  setScale(v: number): void;
  /** Tamaño base de cada partícula. */
  setParticleSize(v: number): void;
  /** Aplica varios parámetros de configuración de golpe. */
  setConfig(patch: Partial<CoreConfig>): void;
  /** Congela la simulación (sigue renderizando el último fotograma). */
  pause(): void;
  /** Reanuda la simulación tras pause(). */
  resume(): void;
  getShape(): string;
  getState(): CoreStateName;
  getConfig(): Readonly<CoreConfig>;
  listShapes(): string[];
  listStates(): string[];
  registerShape(name: string, generator: ShapeGenerator): void;
  dispose(): void;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export async function mount(element: HTMLElement, userConfig?: Partial<CoreConfig>): Promise<JarvisCoreHandle> {
  const config: CoreConfig = mergeConfig(userConfig);
  const initial = await generateShape(config.shape, config.particleCount, { radius: config.coreRadius });

  const ref = createRef<CoreEngineHandle>();
  const root: Root = createRoot(element);
  root.render(createElement(CoreEngine, { ref, config, initialPositions: initial }));

  // R3F monta la escena de forma asíncrona (y una pestaña oculta puede
  // retrasarla). Las órdenes que lleguen antes de tiempo NO se pierden:
  // quedan pendientes y se aplican en cuanto el sistema esté listo.
  let pendingState: CoreStateName | null = null;
  let pendingShape: { name: string; ctx?: Partial<ShapeContext> } | null = null;
  let flushTimer: number | null = null;
  const ensureFlush = () => {
    if (flushTimer !== null) return;
    flushTimer = window.setInterval(() => {
      if (!ref.current) return;
      if (pendingState) { ref.current.setState(pendingState); pendingState = null; }
      if (pendingShape) { void ref.current.setShape(pendingShape.name, pendingShape.ctx); pendingShape = null; }
      if (!pendingState && !pendingShape && flushTimer !== null) {
        clearInterval(flushTimer);
        flushTimer = null;
      }
    }, 120);
  };

  // dar una oportunidad razonable a que el sistema arranque ya mismo
  await new Promise<void>(resolve => {
    const t0 = performance.now();
    const check = () => {
      if (ref.current || document.hidden || performance.now() - t0 > 8000) return resolve();
      setTimeout(check, 60);
    };
    check();
  });

  return {
    async setShape(name, ctx) {
      if (ref.current) { await ref.current.setShape(name, ctx); }
      else { pendingShape = { name, ctx }; ensureFlush(); }
    },
    setState(name) {
      if (!isCoreState(name)) { console.warn(`[JarvisCore] estado desconocido: ${name}`); return; }
      if (ref.current) ref.current.setState(name);
      else { pendingState = name; ensureFlush(); }
    },
    setAudioLevel(level) { ref.current?.setAudioLevel(level); },
    // Estos setters mutan el MISMO objeto config que el motor lee cada
    // fotograma: el cambio se ve al instante, sin recrear nada.
    setColor(hex) { config.color = hex; },
    setEnergy(v) { config.energyBias = clamp(v, 0, 1); },
    setGlow(v) { config.glow = Math.max(0, v); },
    setBloom(v) { config.bloom = Math.max(0, v); },
    setBloomThreshold(v) { config.bloomThreshold = clamp(v, 0, 1); },
    setNoiseIntensity(v) { config.noiseStrength = Math.max(0, v); },
    setMorphSpeed(v) { config.transitionSpeed = Math.max(0.05, v); },
    setRotation(v) { config.rotationSpeed = v; },
    setScale(v) { config.coreRadius = Math.max(0.2, v); },
    setParticleSize(v) { config.particleSize = Math.max(0.1, v); },
    setConfig(patch) { Object.assign(config, patch); },
    pause() { config.paused = true; },
    resume() { config.paused = false; },
    getShape() { return ref.current?.getShape() ?? pendingShape?.name ?? config.shape; },
    getState() { return ref.current?.getState() ?? pendingState ?? "esperando"; },
    getConfig() { return { ...config }; },
    listShapes,
    listStates() { return Object.keys(CORE_STATES); },
    registerShape,
    dispose() {
      if (flushTimer !== null) { clearInterval(flushTimer); flushTimer = null; }
      root.unmount();
    },
  };
}

export { registerShape, registerAsyncShape, listShapes };
export type { CoreConfig };
