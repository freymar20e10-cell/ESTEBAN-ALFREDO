/**
 * AnimationManager — la fisiología del núcleo.
 * Mantiene los parámetros "vivos" (pulso, ruido, energía, color...) y los
 * desliza suavemente hacia los del estado actual. Ningún cambio de estado
 * produce un salto: todo respira hacia su nuevo valor.
 */
import * as THREE from "three";
import type { CoreConfig } from "../config/CoreConfig";
import { CORE_STATES, type CoreStateName } from "../config/CoreState";

export interface LiveParams {
  pulseSpeed: number;
  pulseAmp: number;
  noiseStrength: number;
  speed: number;
  energy: number;
  wave: number;
  expand: number;
  jitter: number;
  dim: number;
  vortex: number;
  audio: number;
  color: THREE.Color;
}

export class AnimationManager {
  state: CoreStateName = "esperando";
  private targetAudio = 0;
  readonly live: LiveParams;
  private readonly targetColor = new THREE.Color();

  constructor(private config: CoreConfig) {
    const st = CORE_STATES[this.state];
    this.live = {
      pulseSpeed: config.pulseSpeed * st.pulseSpeed,
      pulseAmp: config.pulseIntensity * st.pulseIntensity,
      noiseStrength: config.noiseStrength * st.noiseStrength,
      speed: config.particleSpeed * st.speed,
      energy: st.energy,
      wave: st.wave,
      expand: st.expand,
      jitter: st.jitter,
      dim: st.dim,
      vortex: 0,
      audio: 0,
      color: new THREE.Color(config.color),
    };
  }

  setState(name: CoreStateName): void { this.state = name; }
  setAudioLevel(v: number): void { this.targetAudio = THREE.MathUtils.clamp(v, 0, 1); }
  setConfig(config: CoreConfig): void { this.config = config; }

  /** Desliza todos los parámetros hacia el estado objetivo. Llamar cada frame. */
  update(delta: number, vortexTarget: number): void {
    const st = CORE_STATES[this.state];
    const cfg = this.config;
    const k = Math.min(1, delta * 2.2 * Math.max(0.1, cfg.transitionSpeed));
    const l = this.live;

    l.pulseSpeed += (cfg.pulseSpeed * st.pulseSpeed - l.pulseSpeed) * k;
    l.pulseAmp += (cfg.pulseIntensity * st.pulseIntensity - l.pulseAmp) * k;
    l.noiseStrength += (cfg.noiseStrength * st.noiseStrength - l.noiseStrength) * k;
    l.speed += (cfg.particleSpeed * st.speed - l.speed) * k;
    const energyTarget = Math.min(1, Math.max(0, st.energy + cfg.energyBias));
    l.energy += (energyTarget - l.energy) * k;
    l.wave += (st.wave - l.wave) * k;
    l.expand += (st.expand - l.expand) * k;
    l.jitter += (st.jitter - l.jitter) * k;
    l.dim += (st.dim - l.dim) * k;
    l.vortex += (vortexTarget - l.vortex) * k;
    l.audio += (this.targetAudio - l.audio) * Math.min(1, delta * 8);

    this.targetColor.set(st.color ?? cfg.color);
    l.color.lerp(this.targetColor, k);
  }

  /** Factor de escala con respiración incluida (1 ± pulso). */
  breathScale(time: number): number {
    if (this.config.idleAnimation === "none") return 1;
    return 1 + Math.sin(time * this.live.pulseSpeed) * this.live.pulseAmp;
  }
}
