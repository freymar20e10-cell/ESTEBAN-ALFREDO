// Jarvis states -> color + motion character for The Core.
// Estados principales de Jarvis (según el flujo del usuario):
//   escuchando (azul)  -> neutral / a la espera
//   pensando   (naranja) -> procesando / ejecutando una acción
//   listo      (verde) -> acción completada con éxito
//   error      (rojo)  -> ocurrió un problema

export type JarvisState = "escuchando" | "pensando" | "listo" | "error";

export interface StateStyle {
  id: JarvisState;
  label: string;
  // rgb 0..1 for the particle color
  color: [number, number, number];
  // breathing speed & amplitude multipliers
  breathSpeed: number;
  breathAmp: number;
  // turbulence / energy of the particle motion
  energy: number;
}

export const STATES: Record<JarvisState, StateStyle> = {
  escuchando: {
    id: "escuchando",
    label: "Escuchando",
    color: [0.2, 0.55, 1.0], // azul
    breathSpeed: 0.9,
    breathAmp: 0.07,
    energy: 0.25,
  },
  pensando: {
    id: "pensando",
    label: "Pensando",
    color: [1.0, 0.6, 0.12], // naranja
    breathSpeed: 1.6,
    breathAmp: 0.11,
    energy: 0.8,
  },
  listo: {
    id: "listo",
    label: "Listo",
    color: [0.25, 0.9, 0.5], // verde
    breathSpeed: 1.1,
    breathAmp: 0.09,
    energy: 0.4,
  },
  error: {
    id: "error",
    label: "Error",
    color: [1.0, 0.25, 0.35], // rojo
    breathSpeed: 3.0,
    breathAmp: 0.18,
    energy: 1.0,
  },
};

export const STATE_ORDER: JarvisState[] = [
  "escuchando",
  "pensando",
  "listo",
  "error",
];
