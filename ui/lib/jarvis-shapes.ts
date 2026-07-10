// Shape generators for The Core.
// Each returns a Float32Array of xyz positions (length = count * 3),
// scaled roughly to a unit-ish radius so morphing between shapes is smooth.

export type ShapeId =
  | "sphere"
  | "cube"
  | "torus"
  | "ring"
  | "spiral"
  | "wave"
  | "pyramid"
  | "galaxy";

export const SHAPES: { id: ShapeId; label: string }[] = [
  { id: "sphere", label: "Esfera" },
  { id: "cube", label: "Cubo" },
  { id: "torus", label: "Toroide" },
  { id: "ring", label: "Anillos" },
  { id: "spiral", label: "Espiral" },
  { id: "wave", label: "Onda" },
  { id: "pyramid", label: "Pirámide" },
  { id: "galaxy", label: "Galaxia" },
];

const R = 2.2;

function fibonacciSphere(count: number, radius: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = golden * i;
    pos[i * 3] = Math.cos(theta) * r * radius;
    pos[i * 3 + 1] = y * radius;
    pos[i * 3 + 2] = Math.sin(theta) * r * radius;
  }
  return pos;
}

function cube(count: number, size: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const h = size;
  for (let i = 0; i < count; i++) {
    // Distribute across 6 faces
    const face = i % 6;
    const u = (Math.random() * 2 - 1) * h;
    const v = (Math.random() * 2 - 1) * h;
    let x = 0,
      y = 0,
      z = 0;
    switch (face) {
      case 0: x = h; y = u; z = v; break;
      case 1: x = -h; y = u; z = v; break;
      case 2: y = h; x = u; z = v; break;
      case 3: y = -h; x = u; z = v; break;
      case 4: z = h; x = u; y = v; break;
      default: z = -h; x = u; y = v; break;
    }
    pos[i * 3] = x;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = z;
  }
  return pos;
}

function torus(count: number, majorR: number, minorR: number): Float32Array {
  const pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const u = Math.random() * Math.PI * 2;
    const v = Math.random() * Math.PI * 2;
    pos[i * 3] = (majorR + minorR * Math.cos(v)) * Math.cos(u);
    pos[i * 3 + 1] = minorR * Math.sin(v);
    pos[i * 3 + 2] = (majorR + minorR * Math.cos(v)) * Math.sin(u);
  }
  return pos;
}

function ring(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const rings = 3;
  for (let i = 0; i < count; i++) {
    const ringIdx = i % rings;
    const radius = R * (0.6 + ringIdx * 0.28);
    const a = Math.random() * Math.PI * 2;
    const jitter = (Math.random() - 0.5) * 0.12;
    pos[i * 3] = Math.cos(a) * radius + jitter;
    pos[i * 3 + 1] = (Math.random() - 0.5) * 0.1;
    pos[i * 3 + 2] = Math.sin(a) * radius + jitter;
  }
  return pos;
}

function spiral(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const turns = 5;
  for (let i = 0; i < count; i++) {
    const t = i / count;
    const a = t * Math.PI * 2 * turns;
    const radius = t * R * 1.4;
    pos[i * 3] = Math.cos(a) * radius;
    pos[i * 3 + 1] = (t - 0.5) * R * 1.6;
    pos[i * 3 + 2] = Math.sin(a) * radius;
  }
  return pos;
}

function wave(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const side = Math.ceil(Math.sqrt(count));
  for (let i = 0; i < count; i++) {
    const gx = (i % side) / side - 0.5;
    const gz = Math.floor(i / side) / side - 0.5;
    const x = gx * R * 3;
    const z = gz * R * 3;
    const y = Math.sin(x * 1.3) * Math.cos(z * 1.3) * 0.9;
    pos[i * 3] = x;
    pos[i * 3 + 1] = y;
    pos[i * 3 + 2] = z;
  }
  return pos;
}

function pyramid(count: number, size: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const apex = [0, size, 0];
  const base = [
    [-size, -size, -size],
    [size, -size, -size],
    [size, -size, size],
    [-size, -size, size],
  ];
  for (let i = 0; i < count; i++) {
    if (i % 5 === 0) {
      // base fill
      const a = base[Math.floor(Math.random() * 4)];
      const b = base[Math.floor(Math.random() * 4)];
      const t = Math.random();
      pos[i * 3] = a[0] + (b[0] - a[0]) * t;
      pos[i * 3 + 1] = -size;
      pos[i * 3 + 2] = a[2] + (b[2] - a[2]) * t;
    } else {
      const edge = base[Math.floor(Math.random() * 4)];
      const t = Math.random();
      pos[i * 3] = edge[0] + (apex[0] - edge[0]) * t;
      pos[i * 3 + 1] = edge[1] + (apex[1] - edge[1]) * t;
      pos[i * 3 + 2] = edge[2] + (apex[2] - edge[2]) * t;
    }
  }
  return pos;
}

function galaxy(count: number): Float32Array {
  const pos = new Float32Array(count * 3);
  const arms = 4;
  for (let i = 0; i < count; i++) {
    const arm = i % arms;
    const t = Math.pow(Math.random(), 0.6);
    const radius = t * R * 1.6;
    const a = arm * ((Math.PI * 2) / arms) + t * 3.5;
    const spread = (1 - t) * 0.5;
    pos[i * 3] = Math.cos(a) * radius + (Math.random() - 0.5) * spread;
    pos[i * 3 + 1] = (Math.random() - 0.5) * spread * 0.6;
    pos[i * 3 + 2] = Math.sin(a) * radius + (Math.random() - 0.5) * spread;
  }
  return pos;
}

export function generateShape(id: ShapeId, count: number): Float32Array {
  switch (id) {
    case "sphere": return fibonacciSphere(count, R);
    case "cube": return cube(count, R * 0.8);
    case "torus": return torus(count, R * 0.9, R * 0.35);
    case "ring": return ring(count);
    case "spiral": return spiral(count);
    case "wave": return wave(count);
    case "pyramid": return pyramid(count, R * 0.85);
    case "galaxy": return galaxy(count);
    default: return fibonacciSphere(count, R);
  }
}
