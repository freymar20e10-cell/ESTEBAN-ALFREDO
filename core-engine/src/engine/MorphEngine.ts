/**
 * MorphEngine — el corazón del cambio de forma.
 * Regla de oro: las partículas NUNCA desaparecen y la geometría NUNCA se
 * recrea. Hay dos buffers (aFrom / aTo) y un uniform uMorph que la GPU
 * interpola. Al terminar una transición, el destino se copia al origen y
 * el motor queda listo para el siguiente morph — cero allocaciones.
 */
import * as THREE from "three";
import { generateShape, type ShapeContext } from "./ShapeRegistry";

export class MorphEngine {
  private from: THREE.BufferAttribute;
  private to: THREE.BufferAttribute;
  private progress = 1;                 // 1 = estable, <1 = en transición
  private pendingToken = 0;             // descarta morphs viejos si llegan tarde
  currentShape: string;

  constructor(
    geometry: THREE.BufferGeometry,
    private count: number,
    initial: Float32Array,
    initialShape: string,
  ) {
    this.from = new THREE.BufferAttribute(initial.slice(), 3);
    this.to = new THREE.BufferAttribute(initial, 3);
    geometry.setAttribute("aFrom", this.from);
    geometry.setAttribute("aTo", this.to);
    this.currentShape = initialShape;
  }

  /** Lanza un morphing hacia una forma registrada. Fluido, sin saltos. */
  async setShape(name: string, ctx: ShapeContext): Promise<void> {
    const token = ++this.pendingToken;
    const target = await generateShape(name, this.count, ctx);
    if (token !== this.pendingToken) return;   // llegó otro morph más nuevo

    // el punto de partida es la mezcla ACTUAL (aunque haya morph a medias):
    // congelamos la interpolación vigente en aFrom y arrancamos de cero.
    const fromArr = this.from.array as Float32Array;
    const toArr = this.to.array as Float32Array;
    if (this.progress < 1) {
      const m = this.eased();
      for (let i = 0; i < fromArr.length; i++) {
        fromArr[i] = fromArr[i] + (toArr[i] - fromArr[i]) * m;
      }
    } else {
      fromArr.set(toArr);
    }
    toArr.set(target);
    this.from.needsUpdate = true;
    this.to.needsUpdate = true;
    this.progress = 0;
    this.currentShape = name;
  }

  /** Avanza la transición. Devuelve el valor para el uniform uMorph. */
  update(delta: number, transitionSpeed: number): number {
    if (this.progress < 1) {
      this.progress = Math.min(1, this.progress + delta * Math.max(0.05, transitionSpeed) * 0.6);
    }
    return this.progress;
  }

  private eased(): number {
    const t = this.progress;
    return t * t * (3 - 2 * t);
  }
}
