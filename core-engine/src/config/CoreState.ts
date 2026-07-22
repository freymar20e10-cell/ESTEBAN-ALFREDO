/**
 * CoreState — los estados vitales del núcleo y cómo modulan al motor.
 * Cada estado define multiplicadores sobre la configuración base; el
 * AnimationManager interpola suavemente entre ellos, así que cambiar de
 * estado nunca produce un salto visual.
 */

export type CoreStateName =
  | "esperando"
  | "escuchando"
  | "pensando"
  | "hablando"
  | "buscando"
  | "trabajando"
  | "durmiendo"
  | "procesando"
  | "error"
  | "arrancando"
  | "apagando"
  | "actualizando"
  | "desconectado";

export interface StateModulation {
  /** Etiqueta legible (la UI puede usarla). */
  label: string;
  /** Color que tiñe el núcleo en este estado (null = color base del config). */
  color: string | null;
  /** Multiplicador de velocidad de pulso. */
  pulseSpeed: number;
  /** Multiplicador de amplitud de pulso. */
  pulseIntensity: number;
  /** Multiplicador de fuerza de ruido (actividad orgánica). */
  noiseStrength: number;
  /** Multiplicador de velocidad de flujo. */
  speed: number;
  /** Energía 0..1: alimenta brillo, twinkle y rotación extra. */
  energy: number;
  /** Ondas radiales (hablando) 0..1. */
  wave: number;
  /** Expansión pulsante (actualizando) 0..1. */
  expand: number;
  /** Inestabilidad de alta frecuencia (error) 0..1. */
  jitter: number;
  /** Atenuación global de brillo (desconectado) 0..1, 1 = normal. */
  dim: number;
}

const S = (m: Partial<StateModulation> & { label: string }): StateModulation => ({
  color: null,
  pulseSpeed: 1,
  pulseIntensity: 1,
  noiseStrength: 1,
  speed: 1,
  energy: 0.25,
  wave: 0,
  expand: 0,
  jitter: 0,
  dim: 1,
  ...m,
});

export const CORE_STATES: Record<CoreStateName, StateModulation> = {
  esperando:    S({ label: "Esperando",    pulseSpeed: 0.7, pulseIntensity: 0.9, noiseStrength: 0.85, speed: 0.6, energy: 0.18 }),
  escuchando:   S({ label: "Escuchando",   pulseSpeed: 1.6, pulseIntensity: 1.7, noiseStrength: 1.0,  speed: 0.9, energy: 0.4 }),
  pensando:     S({ label: "Pensando",     color: "#ffb547", pulseSpeed: 1.9, pulseIntensity: 1.2, noiseStrength: 1.9, speed: 1.6, energy: 0.8 }),
  hablando:     S({ label: "Hablando",     pulseSpeed: 1.2, pulseIntensity: 0.8, noiseStrength: 1.1, speed: 1.1, energy: 0.55, wave: 1 }),
  buscando:     S({ label: "Buscando",     color: "#33e0ff", pulseSpeed: 1.4, pulseIntensity: 1.0, noiseStrength: 1.6, speed: 2.2, energy: 0.7 }),
  trabajando:   S({ label: "Trabajando",   color: "#ffce54", pulseSpeed: 1.5, pulseIntensity: 1.1, noiseStrength: 1.7, speed: 1.4, energy: 0.75 }),
  durmiendo:    S({ label: "En reposo",    color: "#5a7fb0", pulseSpeed: 0.45, pulseIntensity: 0.7, noiseStrength: 0.5, speed: 0.35, energy: 0.1, dim: 0.55 }),
  procesando:   S({ label: "Procesando",   color: "#7c6cff", pulseSpeed: 2.4, pulseIntensity: 1.4, noiseStrength: 2.2, speed: 2.0, energy: 1.0 }),
  error:        S({ label: "Error",        color: "#ff5468", pulseSpeed: 3.2, pulseIntensity: 1.8, noiseStrength: 1.4, speed: 1.3, energy: 0.9, jitter: 1 }),
  arrancando:   S({ label: "Arrancando",   color: "#43e5a0", pulseSpeed: 1.0, pulseIntensity: 1.3, noiseStrength: 1.5, speed: 1.2, energy: 0.85, expand: 1 }),
  apagando:     S({ label: "Apagando",     color: "#3a4a5a", pulseSpeed: 0.5, pulseIntensity: 0.6, noiseStrength: 0.5, speed: 0.3, energy: 0.08, dim: 0.25 }),
  actualizando: S({ label: "Actualizando", color: "#3dffa0", pulseSpeed: 1.1, pulseIntensity: 1.1, noiseStrength: 1.2, speed: 1.0, energy: 0.6, expand: 1 }),
  desconectado: S({ label: "Sin conexión", color: "#5c2f36", pulseSpeed: 0.4, pulseIntensity: 0.5, noiseStrength: 0.4, speed: 0.25, energy: 0.05, dim: 0.35 }),
};

export function isCoreState(name: string): name is CoreStateName {
  return name in CORE_STATES;
}
