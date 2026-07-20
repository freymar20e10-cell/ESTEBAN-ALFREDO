/**
 * Formas "cósmicas": la nebulosa por defecto, galaxia espiral, ADN y el
 * agujero negro. El agujero negro además activa el remolino del shader
 * (uVortex) — la forma pone las partículas en el disco de acreción y el
 * shader las hace orbitar con rotación diferencial.
 */
import type { ShapeGenerator } from "../ShapeRegistry";

/** Nebulosa: centro denso brillante + halo disperso (la forma insignia de JARVIS). */
export const nebula: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const inner = Math.random() < 0.58;
    const r = inner
      ? (0.05 + Math.pow(Math.random(), 2.6) * 0.55) * radius
      : (0.42 + Math.pow(Math.random(), 1.6) * 1.25) * radius;
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(2 * Math.random() - 1);
    p[i * 3] = r * Math.sin(ph) * Math.cos(th);
    p[i * 3 + 1] = r * Math.cos(ph) * 0.72;
    p[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
  }
  return p;
};

/** Galaxia espiral: 4 brazos, centro brillante con volumen, bordes finos. */
export const galaxy: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const arms = 4;
  const R = radius * 1.5;
  for (let i = 0; i < n; i++) {
    // bulbo central con volumen (25%) + brazos (75%)
    if (i % 4 === 0) {
      const r = Math.pow(Math.random(), 2.2) * radius * 0.42;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      p[i * 3] = r * Math.sin(ph) * Math.cos(th);
      p[i * 3 + 1] = r * Math.cos(ph) * 0.55;
      p[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
      continue;
    }
    const arm = i % arms;
    const t = Math.pow(Math.random(), 0.55);
    const r = t * R;
    const a = arm * (Math.PI * 2 / arms) + t * 3.6;
    const spread = (1 - t) * 0.34 + 0.05;
    p[i * 3] = Math.cos(a) * r + (Math.random() - 0.5) * spread;
    p[i * 3 + 1] = (Math.random() - 0.5) * spread * (1.1 - t) * 0.8;
    p[i * 3 + 2] = Math.sin(a) * r + (Math.random() - 0.5) * spread;
  }
  return p;
};

/** Doble hélice de ADN con puentes entre las hebras. */
export const dna: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const turns = 3.2;
  const H = radius * 2.4;
  const r = radius * 0.42;
  for (let i = 0; i < n; i++) {
    const kind = i % 10;
    const t = Math.random();
    const ang = t * Math.PI * 2 * turns;
    const y = (t - 0.5) * H;
    if (kind < 4) {          // hebra A
      p[i * 3] = Math.cos(ang) * r;
      p[i * 3 + 1] = y;
      p[i * 3 + 2] = Math.sin(ang) * r;
    } else if (kind < 8) {   // hebra B (desfasada 180°)
      p[i * 3] = Math.cos(ang + Math.PI) * r;
      p[i * 3 + 1] = y;
      p[i * 3 + 2] = Math.sin(ang + Math.PI) * r;
    } else {                 // puentes entre hebras
      const step = Math.floor(t * turns * 10) / (turns * 10);
      const bang = step * Math.PI * 2 * turns;
      const by = (step - 0.5) * H;
      const s = Math.random() * 2 - 1;
      p[i * 3] = Math.cos(bang) * r * s;
      p[i * 3 + 1] = by;
      p[i * 3 + 2] = Math.sin(bang) * r * s;
    }
  }
  return p;
};

/**
 * Agujero negro: disco de acreción denso con horizonte vacío en el centro
 * y chorros polares tenues. El remolino real lo aplica el shader (uVortex):
 * rotación más rápida cerca del horizonte, como la física manda.
 */
export const blackHole: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const horizon = radius * 0.34;
  for (let i = 0; i < n; i++) {
    if (i % 14 === 0) {      // chorros polares
      const up = Math.random() < 0.5 ? 1 : -1;
      const t = Math.pow(Math.random(), 1.4);
      const rr = 0.05 + t * 0.12;
      const a = Math.random() * Math.PI * 2;
      p[i * 3] = Math.cos(a) * rr;
      p[i * 3 + 1] = up * (horizon + t * radius * 1.5);
      p[i * 3 + 2] = Math.sin(a) * rr;
      continue;
    }
    // disco de acreción: denso junto al horizonte, se difumina hacia afuera
    const t = Math.pow(Math.random(), 2.0);
    const r = horizon * 1.05 + t * radius * 1.5;
    const a = Math.random() * Math.PI * 2;
    const thick = 0.03 + (r / radius) * 0.05;
    p[i * 3] = Math.cos(a) * r;
    p[i * 3 + 1] = (Math.random() - 0.5) * thick * radius;
    p[i * 3 + 2] = Math.sin(a) * r;
  }
  return p;
};
