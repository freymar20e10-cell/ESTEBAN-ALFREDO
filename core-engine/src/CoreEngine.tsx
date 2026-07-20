/**
 * CoreEngine — composición raíz del motor.
 * Monta el Canvas, adapta la resolución automáticamente para sostener
 * 60fps (PerformanceMonitor de drei baja el pixel ratio antes de que se
 * sienta una caída), y expone el API imperativo hacia afuera.
 */
import { Canvas } from "@react-three/fiber";
import { PerformanceMonitor } from "@react-three/drei";
import { forwardRef, useCallback, useImperativeHandle, useRef, useState } from "react";
import type { CoreConfig } from "./config/CoreConfig";
import type { CoreStateName } from "./config/CoreState";
import { ParticleSystem, type ParticleSystemHandle } from "./engine/ParticleSystem";
import type { ShapeContext } from "./engine/ShapeRegistry";

export interface CoreEngineHandle {
  setShape(name: string, ctx?: Partial<ShapeContext>): Promise<void>;
  setState(name: CoreStateName): void;
  setAudioLevel(v: number): void;
  getShape(): string;
  getState(): CoreStateName;
}

interface Props {
  config: CoreConfig;
  initialPositions: Float32Array;
}

export const CoreEngine = forwardRef<CoreEngineHandle, Props>(function CoreEngine(
  { config, initialPositions },
  ref,
) {
  const system = useRef<ParticleSystemHandle>(null);
  const [dprMax, setDprMax] = useState(config.maxPixelRatio);

  // R3F monta la escena de forma asíncrona (una pestaña oculta puede
  // demorarla). Las órdenes que lleguen antes NO se pierden: quedan aquí
  // y se aplican en cuanto el sistema de partículas avisa que está listo.
  const pending = useRef<{ state?: CoreStateName; shape?: { name: string; ctx?: Partial<ShapeContext> } }>({});
  const handleReady = useCallback(() => {
    const p = pending.current;
    if (p.state) system.current?.setState(p.state);
    if (p.shape) void system.current?.setShape(p.shape.name, p.shape.ctx);
    pending.current = {};
  }, []);

  useImperativeHandle(ref, () => ({
    async setShape(name, ctx) {
      if (system.current) await system.current.setShape(name, ctx);
      else pending.current.shape = { name, ctx };
    },
    setState(name) {
      if (system.current) system.current.setState(name);
      else pending.current.state = name;
    },
    setAudioLevel(v) { system.current?.setAudioLevel(v); },
    getShape() { return system.current?.getShape() ?? pending.current.shape?.name ?? config.shape; },
    getState() { return system.current?.getState() ?? pending.current.state ?? "esperando"; },
  }), [config.shape]);

  return (
    <Canvas
      camera={{ position: [0, 0.6, 7.4], fov: 50 }}
      dpr={[0.75, dprMax]}
      gl={{ antialias: false, alpha: true, powerPreference: "high-performance" }}
      style={{ width: "100%", height: "100%", display: "block" }}
    >
      <PerformanceMonitor
        onDecline={() => setDprMax(d => Math.max(0.75, d - 0.25))}
        onIncline={() => setDprMax(d => Math.min(config.maxPixelRatio, d + 0.25))}
      >
        <ParticleSystem ref={system} config={config} initialPositions={initialPositions} onReady={handleReady} />
      </PerformanceMonitor>
    </Canvas>
  );
});
