/**
 * ShapeRegistry — el catálogo de formas del núcleo.
 * Agregar una forma nueva NO requiere tocar el motor: basta con
 * registerShape('nombre', generador). El MorphEngine consume de aquí.
 */
import { sphere, cube, torus, ring, cylinder, cone } from "./shapes/basic";
import { nebula, galaxy, dna, blackHole } from "./shapes/cosmic";
import { textShape, svgShape } from "./shapes/raster";
import { modelShape } from "./shapes/model";

export interface ShapeContext {
  radius: number;
  /** Texto para la forma 'text'. */
  text?: string;
  /** Markup SVG para la forma 'svg'. */
  svg?: string;
  /** URL de modelo para la forma 'model'. */
  url?: string;
}

export type ShapeGenerator = (n: number, ctx: ShapeContext) => Float32Array;
export type AsyncShapeGenerator = (n: number, ctx: ShapeContext) => Promise<Float32Array>;

const sync = new Map<string, ShapeGenerator>();
const async_ = new Map<string, AsyncShapeGenerator>();

export function registerShape(name: string, gen: ShapeGenerator): void {
  sync.set(name.toLowerCase(), gen);
}
export function registerAsyncShape(name: string, gen: AsyncShapeGenerator): void {
  async_.set(name.toLowerCase(), gen);
}
export function listShapes(): string[] {
  return [...sync.keys(), ...async_.keys()];
}

/** Genera las posiciones de una forma. Siempre resuelve (fallback: nebulosa). */
export async function generateShape(name: string, n: number, ctx: ShapeContext): Promise<Float32Array> {
  const key = name.toLowerCase();
  const s = sync.get(key);
  if (s) return s(n, ctx);
  const a = async_.get(key);
  if (a) {
    try { return await a(n, ctx); } catch { return nebula(n, ctx); }
  }
  return nebula(n, ctx);
}

// ── catálogo integrado ──
registerShape("nebula", nebula);
registerShape("sphere", sphere);
registerShape("cube", cube);
registerShape("torus", torus);
registerShape("ring", ring);
registerShape("cylinder", cylinder);
registerShape("cone", cone);
registerShape("galaxy", galaxy);
registerShape("dna", dna);
registerShape("blackhole", blackHole);
registerShape("text", (n, ctx) => textShape(n, ctx.radius, ctx.text ?? "JARVIS"));
registerAsyncShape("svg", (n, ctx) => svgShape(n, ctx.radius, ctx.svg ?? ""));
registerAsyncShape("model", (n, ctx) => modelShape(n, ctx.radius, ctx.url ?? ""));
