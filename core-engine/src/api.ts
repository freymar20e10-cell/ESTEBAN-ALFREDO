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
  getShape(): string;
  getState(): CoreStateName;
  listShapes(): string[];
  listStates(): string[];
  registerShape(name: string, generator: ShapeGenerator): void;
  dispose(): void;
}

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
    getShape() { return ref.current?.getShape() ?? pendingShape?.name ?? config.shape; },
    getState() { return ref.current?.getState() ?? pendingState ?? "esperando"; },
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
