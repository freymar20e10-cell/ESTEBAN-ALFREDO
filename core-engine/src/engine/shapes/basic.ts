/**
 * Formas geométricas básicas. Cada generador devuelve N posiciones (xyz)
 * distribuidas SOBRE la forma — determinísticas cuando importa (esfera
 * fibonacci) y bien repartidas cuando la superficie lo pide.
 */
import type { ShapeGenerator } from "../ShapeRegistry";

export const sphere: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const th = golden * i;
    p[i * 3] = Math.cos(th) * r * radius;
    p[i * 3 + 1] = y * radius;
    p[i * 3 + 2] = Math.sin(th) * r * radius;
  }
  return p;
};

export const cube: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const h = radius * 0.78;
  for (let i = 0; i < n; i++) {
    const face = i % 6;
    const u = (Math.random() * 2 - 1) * h;
    const v = (Math.random() * 2 - 1) * h;
    const s = [
      [h, u, v], [-h, u, v],
      [u, h, v], [u, -h, v],
      [u, v, h], [u, v, -h],
    ][face];
    p[i * 3] = s[0]; p[i * 3 + 1] = s[1]; p[i * 3 + 2] = s[2];
  }
  return p;
};

export const torus: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const R = radius * 0.82, r = radius * 0.3;
  for (let i = 0; i < n; i++) {
    const u = (i / n) * Math.PI * 2 * 97;      // envuelve muchas vueltas: cobertura pareja
    const v = Math.random() * Math.PI * 2;
    p[i * 3] = (R + r * Math.cos(v)) * Math.cos(u);
    p[i * 3 + 1] = r * Math.sin(v);
    p[i * 3 + 2] = (R + r * Math.cos(v)) * Math.sin(u);
  }
  return p;
};

export const ring: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const rings = 3;
  for (let i = 0; i < n; i++) {
    const ri = i % rings;
    const rr = radius * (0.62 + ri * 0.26);
    const a = Math.random() * Math.PI * 2;
    p[i * 3] = Math.cos(a) * rr + (Math.random() - 0.5) * 0.08;
    p[i * 3 + 1] = (Math.random() - 0.5) * 0.09;
    p[i * 3 + 2] = Math.sin(a) * rr + (Math.random() - 0.5) * 0.08;
  }
  return p;
};

export const cylinder: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const r = radius * 0.62, h = radius * 1.5;
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2;
    const onCap = Math.random() < 0.18;
    if (onCap) {
      const rr = Math.sqrt(Math.random()) * r;
      p[i * 3] = Math.cos(a) * rr;
      p[i * 3 + 1] = (Math.random() < 0.5 ? -1 : 1) * h * 0.5;
      p[i * 3 + 2] = Math.sin(a) * rr;
    } else {
      p[i * 3] = Math.cos(a) * r;
      p[i * 3 + 1] = (Math.random() - 0.5) * h;
      p[i * 3 + 2] = Math.sin(a) * r;
    }
  }
  return p;
};

export const cone: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const r = radius * 0.85, h = radius * 1.6;
  for (let i = 0; i < n; i++) {
    const onBase = Math.random() < 0.22;
    const a = Math.random() * Math.PI * 2;
    if (onBase) {
      const rr = Math.sqrt(Math.random()) * r;
      p[i * 3] = Math.cos(a) * rr;
      p[i * 3 + 1] = -h * 0.45;
      p[i * 3 + 2] = Math.sin(a) * rr;
    } else {
      const t = Math.random();                 // 0 = punta, 1 = base
      const rr = r * t;
      p[i * 3] = Math.cos(a) * rr;
      p[i * 3 + 1] = h * 0.55 - t * h;
      p[i * 3 + 2] = Math.sin(a) * rr;
    }
  }
  return p;
};
