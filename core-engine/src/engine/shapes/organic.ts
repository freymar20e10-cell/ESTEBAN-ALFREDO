/**
 * Formas orgánicas del set "Particle Flow" de la referencia: corazón,
 * mariposa, loto, medusa, saturno, tornado y flor. Todas paramétricas
 * (nada pregrabado): se muestrean matemáticamente para que las partículas
 * cubran la silueta con volumen y buena densidad.
 */
import type { ShapeGenerator } from "../ShapeRegistry";

/** Corazón 3D: contorno clásico relleno hacia el centro, con grosor que se afina. */
export const heart: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const s = radius / 17;
  for (let i = 0; i < n; i++) {
    const t = Math.random() * Math.PI * 2;
    const ox = 16 * Math.pow(Math.sin(t), 3);
    const oy = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t);
    const f = Math.sqrt(Math.random());          // 0 centro .. 1 borde
    const z = (Math.random() - 0.5) * (1 - f) * radius * 0.62;
    p[i * 3] = ox * f * s;
    p[i * 3 + 1] = oy * f * s + radius * 0.1;
    p[i * 3 + 2] = z;
  }
  return p;
};

/** Mariposa: curva de Fay (dos alas simétricas) con leve grosor. */
export const butterfly: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const s = radius / 3.1;
  for (let i = 0; i < n; i++) {
    const t = Math.random() * Math.PI * 2 * 6;
    const r = Math.exp(Math.sin(t)) - 2 * Math.cos(4 * t) + Math.pow(Math.sin((2 * t - Math.PI) / 24), 5);
    const f = 0.7 + Math.random() * 0.3;
    p[i * 3] = Math.sin(t) * r * f * s;
    p[i * 3 + 1] = Math.cos(t) * r * f * s;
    p[i * 3 + 2] = (Math.random() - 0.5) * 0.14 * radius;
  }
  return p;
};

/** Loto: pétalos en capas que se abren y se curvan hacia arriba. */
export const lotus: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const layers = 3;
  for (let i = 0; i < n; i++) {
    const layer = i % layers;
    const petals = 6 + layer * 2;
    const a = Math.random() * Math.PI * 2;
    const petal = Math.abs(Math.cos((petals * a) / 2));   // perfil de pétalo 0..1
    const t = Math.pow(Math.random(), 0.6);
    const rr = (0.42 + layer * 0.34) * radius * (0.28 + 0.72 * petal) * t;
    const lift = (1 - t) * (0.2 + layer * 0.32) * radius;
    p[i * 3] = Math.cos(a) * rr;
    p[i * 3 + 1] = -radius * 0.24 + lift + layer * 0.08 * radius;
    p[i * 3 + 2] = Math.sin(a) * rr;
  }
  return p;
};

/** Medusa: campana semiesférica + tentáculos ondulantes que cuelgan. */
export const jellyfish: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    if (i % 2 === 0) {
      const th = Math.random() * Math.PI * 2;
      const ph = Math.random() * Math.PI * 0.5;          // media esfera superior
      const r = radius * 0.92;
      p[i * 3] = r * Math.sin(ph) * Math.cos(th);
      p[i * 3 + 1] = radius * 0.4 + r * Math.cos(ph) * 0.7;
      p[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    } else {
      const strand = Math.floor(Math.random() * 11);
      const a = (strand / 11) * Math.PI * 2;
      const br = radius * (0.15 + 0.4 * Math.random());
      const t = Math.random();
      const wob = Math.sin(t * 8 + strand) * 0.13 * radius;
      p[i * 3] = Math.cos(a) * br + wob;
      p[i * 3 + 1] = radius * 0.4 - t * radius * 1.9;
      p[i * 3 + 2] = Math.sin(a) * br + Math.cos(t * 8 + strand) * 0.13 * radius;
    }
  }
  return p;
};

/** Saturno: planeta esférico + anillo inclinado de partículas. */
export const saturn: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const tilt = 0.42, c = Math.cos(tilt), sn = Math.sin(tilt);
  for (let i = 0; i < n; i++) {
    if (i % 3 !== 0) {
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      const r = radius * 0.6;
      p[i * 3] = r * Math.sin(ph) * Math.cos(th);
      p[i * 3 + 1] = r * Math.cos(ph);
      p[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    } else {
      const a = Math.random() * Math.PI * 2;
      const rr = radius * (1.08 + Math.random() * 0.5);
      const x = Math.cos(a) * rr;
      let y = (Math.random() - 0.5) * 0.03 * radius;
      let z = Math.sin(a) * rr;
      [y, z] = [y * c - z * sn, y * sn + z * c];
      p[i * 3] = x; p[i * 3 + 1] = y; p[i * 3 + 2] = z;
    }
  }
  return p;
};

/** Tornado: embudo que gira y se ensancha hacia arriba. */
export const tornado: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const turns = 5;
  for (let i = 0; i < n; i++) {
    const t = Math.pow(Math.random(), 0.7);              // 0 abajo .. 1 arriba
    const rr = (0.08 + t * 0.92) * radius * 0.95;
    const a = t * Math.PI * 2 * turns + Math.random() * 0.7;
    p[i * 3] = Math.cos(a) * rr;
    p[i * 3 + 1] = (t - 0.5) * radius * 2.7;
    p[i * 3 + 2] = Math.sin(a) * rr;
  }
  return p;
};

/** Flor de durazno: cinco pétalos planos con leve relieve. */
export const peachBlossom: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2;
    const petal = Math.abs(Math.cos(2.5 * a));           // cinco pétalos
    const t = Math.sqrt(Math.random());
    const rr = radius * 1.12 * (0.24 + 0.76 * petal) * t;
    p[i * 3] = Math.cos(a) * rr;
    p[i * 3 + 1] = Math.sin(a) * rr;
    p[i * 3 + 2] = (Math.random() - 0.5) * 0.1 * radius + (1 - t) * 0.16 * radius;
  }
  return p;
};
