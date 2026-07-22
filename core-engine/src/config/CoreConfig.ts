/**
 * CoreConfig — todos los parámetros del núcleo en un solo lugar.
 * Nada está "quemado" en el motor: quien monta el núcleo puede ajustar
 * cualquier valor aquí sin tocar shaders ni sistemas internos.
 */

export type ShapeName = string;

export interface CoreConfig {
  /** Cantidad de partículas. Se fija al montar (los buffers se crean una vez). */
  particleCount: number;
  /** Tamaño base de cada partícula (multiplicador). */
  particleSize: number;
  /** Velocidad global del flujo orgánico (multiplica el tiempo del ruido). */
  particleSpeed: number;
  /** Rotación automática del núcleo completo (rad/seg aprox). */
  rotationSpeed: number;
  /** Velocidad de la respiración/pulso. */
  pulseSpeed: number;
  /** Amplitud de la respiración/pulso (0..1). */
  pulseIntensity: number;
  /** Escala espacial del ruido (más alto = detalles más finos). */
  noiseScale: number;
  /** Fuerza del desplazamiento por curl noise. */
  noiseStrength: number;
  /** Intensidad del brillo del centro y de las partículas calientes (0..1). */
  glow: number;
  /** Opacidad global de las partículas (0..1). */
  opacity: number;
  /** Radio base del núcleo en unidades de mundo. */
  coreRadius: number;
  /** Velocidad de las transiciones (morphing y cambios de estado). 1 = ~1s. */
  transitionSpeed: number;
  /** Color base (hex). Los estados pueden teñirlo temporalmente. */
  color: string;
  /** Color del centro caliente. */
  hotColor: string;
  /** Forma inicial. */
  shape: ShapeName;
  /** Animación en reposo: 'breath' respira, 'none' queda estático. */
  idleAnimation: "breath" | "none";
  /** Influencia del mouse sobre las partículas (0 = ninguna). Sutil por diseño. */
  mouseInfluence: number;
  /** Desorden de llegada en el morphing (0 = todas a la vez, 1 = muy escalonado). */
  morphStagger: number;
  /** Límite de devicePixelRatio (rendimiento). */
  maxPixelRatio: number;
  /** Intensidad del bloom (resplandor cinemático). 0 = apagado. Suave por diseño. */
  bloom: number;
  /** Umbral de luminancia del bloom: solo brilla lo más brillante (0..1). */
  bloomThreshold: number;
  /** Radio de difusión del bloom (0..1). */
  bloomRadius: number;
  /** Energía extra sumada a la del estado (0..1). La API la ajusta en vivo. */
  energyBias: number;
  /** Si true, congela la simulación (pause/resume de la API). */
  paused: boolean;
}

export const DEFAULT_CONFIG: CoreConfig = {
  particleCount: 12000,
  particleSize: 1.05,
  particleSpeed: 1.0,
  rotationSpeed: 0.05,
  pulseSpeed: 0.9,
  pulseIntensity: 0.055,
  noiseScale: 0.6,
  noiseStrength: 0.17,
  glow: 0.95,
  opacity: 0.92,
  coreRadius: 2.1,
  transitionSpeed: 0.9,
  color: "#3fd9ff",
  hotColor: "#fff2d6",   // ignición cálida tipo reactor de Titán (ojo de BT-7274)
  shape: "nebula",
  idleAnimation: "breath",
  mouseInfluence: 0.35,
  morphStagger: 0.55,
  maxPixelRatio: 1.5,
  bloom: 0.55,          // resplandor sutil: da vida sin encandilar
  bloomThreshold: 0.35, // solo el centro caliente florece
  bloomRadius: 0.6,
  energyBias: 0,
  paused: false,
};

export function mergeConfig(partial?: Partial<CoreConfig>): CoreConfig {
  return { ...DEFAULT_CONFIG, ...(partial ?? {}) };
}
