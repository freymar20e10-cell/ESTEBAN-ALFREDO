/**
 * Formas "científicas": átomo, red neuronal, constelación y cristal.
 * Cada generador reparte las N partículas sobre la estructura de forma
 * determinística en lo que importa (órbitas, nodos) y con dispersión
 * controlada donde da volumen.
 */
import type { ShapeGenerator } from "../ShapeRegistry";

/** Átomo: núcleo denso + electrones en órbitas elípticas inclinadas. */
export const atom: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const orbits = 3;
  const planes = [
    [0, 0], [Math.PI / 3, 0], [Math.PI / 3, Math.PI * 2 / 3],
  ];
  for (let i = 0; i < n; i++) {
    if (i % 5 === 0) {
      // núcleo compacto
      const r = Math.pow(Math.random(), 1.8) * radius * 0.28;
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      p[i * 3] = r * Math.sin(ph) * Math.cos(th);
      p[i * 3 + 1] = r * Math.cos(ph);
      p[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    } else {
      const o = i % orbits;
      const [tiltX, tiltY] = planes[o];
      const a = Math.random() * Math.PI * 2;
      const rr = radius * 1.35;
      let x = Math.cos(a) * rr, y = Math.sin(a) * rr * 0.55, z = 0;
      // inclinar la órbita
      const cy = Math.cos(tiltY), sy = Math.sin(tiltY);
      [x, z] = [x * cy - z * sy, x * sy + z * cy];
      const cx = Math.cos(tiltX), sx = Math.sin(tiltX);
      [y, z] = [y * cx - z * sx, y * sx + z * cx];
      const j = 0.04 * radius;
      p[i * 3] = x + (Math.random() - 0.5) * j;
      p[i * 3 + 1] = y + (Math.random() - 0.5) * j;
      p[i * 3 + 2] = z + (Math.random() - 0.5) * j;
    }
  }
  return p;
};

/** Red neuronal: nodos distribuidos en capas con partículas en los enlaces. */
export const neuralnet: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const layers = 5;
  const perLayer = 7;
  const nodes: [number, number, number][] = [];
  for (let L = 0; L < layers; L++) {
    const x = (L / (layers - 1) - 0.5) * radius * 2.6;
    for (let k = 0; k < perLayer; k++) {
      const y = (k / (perLayer - 1) - 0.5) * radius * 2.0;
      const z = (Math.random() - 0.5) * radius * 0.6;
      nodes.push([x, y, z]);
    }
  }
  for (let i = 0; i < n; i++) {
    if (i % 6 === 0) {
      // partícula en un nodo (con pequeño halo)
      const nd = nodes[Math.floor(Math.random() * nodes.length)];
      const j = 0.06 * radius;
      p[i * 3] = nd[0] + (Math.random() - 0.5) * j;
      p[i * 3 + 1] = nd[1] + (Math.random() - 0.5) * j;
      p[i * 3 + 2] = nd[2] + (Math.random() - 0.5) * j;
    } else {
      // partícula sobre un enlace entre capas adyacentes
      const L = Math.floor(Math.random() * (layers - 1));
      const a = nodes[L * perLayer + Math.floor(Math.random() * perLayer)];
      const b = nodes[(L + 1) * perLayer + Math.floor(Math.random() * perLayer)];
      const t = Math.random();
      p[i * 3] = a[0] + (b[0] - a[0]) * t;
      p[i * 3 + 1] = a[1] + (b[1] - a[1]) * t;
      p[i * 3 + 2] = a[2] + (b[2] - a[2]) * t;
    }
  }
  return p;
};

/** Constelación: cúmulos brillantes (estrellas) unidos por líneas tenues. */
export const constellation: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const starCount = 14;
  const stars: [number, number, number][] = [];
  for (let s = 0; s < starCount; s++) {
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(2 * Math.random() - 1);
    const r = radius * (0.5 + Math.random() * 0.9);
    stars.push([
      r * Math.sin(ph) * Math.cos(th),
      r * Math.cos(ph) * 0.85,
      r * Math.sin(ph) * Math.sin(th),
    ]);
  }
  for (let i = 0; i < n; i++) {
    if (i % 3 === 0) {
      const st = stars[Math.floor(Math.random() * starCount)];
      const j = 0.05 * radius;
      p[i * 3] = st[0] + (Math.random() - 0.5) * j;
      p[i * 3 + 1] = st[1] + (Math.random() - 0.5) * j;
      p[i * 3 + 2] = st[2] + (Math.random() - 0.5) * j;
    } else {
      const a = stars[Math.floor(Math.random() * starCount)];
      const b = stars[Math.floor(Math.random() * starCount)];
      const t = Math.random();
      p[i * 3] = a[0] + (b[0] - a[0]) * t;
      p[i * 3 + 1] = a[1] + (b[1] - a[1]) * t;
      p[i * 3 + 2] = a[2] + (b[2] - a[2]) * t;
    }
  }
  return p;
};

/** Cristal: bipirámide facetada (dos conos base con base) con aristas marcadas. */
export const crystal: ShapeGenerator = (n, { radius }) => {
  const p = new Float32Array(n * 3);
  const facets = 6;
  const h = radius * 1.5;
  const r = radius * 0.8;
  const verts: [number, number, number][] = [];
  for (let f = 0; f < facets; f++) {
    const a = (f / facets) * Math.PI * 2;
    verts.push([Math.cos(a) * r, 0, Math.sin(a) * r]);
  }
  const top: [number, number, number] = [0, h, 0];
  const bot: [number, number, number] = [0, -h, 0];
  for (let i = 0; i < n; i++) {
    const f = i % facets;
    const v = verts[f];
    const apex = Math.random() < 0.5 ? top : bot;
    if (i % 4 === 0) {
      // arista del cinturón ecuatorial
      const v2 = verts[(f + 1) % facets];
      const t = Math.random();
      p[i * 3] = v[0] + (v2[0] - v[0]) * t;
      p[i * 3 + 1] = (Math.random() - 0.5) * 0.04 * radius;
      p[i * 3 + 2] = v[2] + (v2[2] - v[2]) * t;
    } else {
      // arista hacia la punta
      const t = Math.random();
      p[i * 3] = v[0] + (apex[0] - v[0]) * t + (Math.random() - 0.5) * 0.03 * radius;
      p[i * 3 + 1] = v[1] + (apex[1] - v[1]) * t;
      p[i * 3 + 2] = v[2] + (apex[2] - v[2]) * t + (Math.random() - 0.5) * 0.03 * radius;
    }
  }
  return p;
};
