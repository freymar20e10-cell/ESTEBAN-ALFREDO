/**
 * Modelos 3D (GLTF / OBJ / geometría three) → partículas.
 * Se muestrea la superficie de las mallas con área ponderada, así los
 * triángulos grandes reciben más partículas y la silueta queda fiel.
 */
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";

export function sampleGeometry(geo: THREE.BufferGeometry, n: number, radius: number): Float32Array {
  const nonIndexed = geo.index ? geo.toNonIndexed() : geo;
  const pos = nonIndexed.getAttribute("position");
  const triCount = pos.count / 3;
  const out = new Float32Array(n * 3);
  if (!triCount) return out;

  // acumular áreas para muestreo proporcional
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  const ab = new THREE.Vector3(), ac = new THREE.Vector3();
  const areas = new Float32Array(triCount);
  let total = 0;
  for (let i = 0; i < triCount; i++) {
    a.fromBufferAttribute(pos, i * 3);
    b.fromBufferAttribute(pos, i * 3 + 1);
    c.fromBufferAttribute(pos, i * 3 + 2);
    const area = ab.subVectors(b, a).cross(ac.subVectors(c, a)).length() * 0.5;
    total += area;
    areas[i] = total;
  }

  for (let i = 0; i < n; i++) {
    const target = Math.random() * total;
    let lo = 0, hi = triCount - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (areas[mid] < target) lo = mid + 1; else hi = mid; }
    a.fromBufferAttribute(pos, lo * 3);
    b.fromBufferAttribute(pos, lo * 3 + 1);
    c.fromBufferAttribute(pos, lo * 3 + 2);
    let u = Math.random(), v = Math.random();
    if (u + v > 1) { u = 1 - u; v = 1 - v; }
    out[i * 3]     = a.x + (b.x - a.x) * u + (c.x - a.x) * v;
    out[i * 3 + 1] = a.y + (b.y - a.y) * u + (c.y - a.y) * v;
    out[i * 3 + 2] = a.z + (b.z - a.z) * u + (c.z - a.z) * v;
  }

  // normalizar al radio del núcleo, centrado
  const box = new THREE.Box3().setFromBufferAttribute(pos as THREE.BufferAttribute);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const scale = (radius * 1.7) / Math.max(size.x, size.y, size.z, 1e-6);
  for (let i = 0; i < n; i++) {
    out[i * 3]     = (out[i * 3] - center.x) * scale;
    out[i * 3 + 1] = (out[i * 3 + 1] - center.y) * scale;
    out[i * 3 + 2] = (out[i * 3 + 2] - center.z) * scale;
  }
  return out;
}

function collectGeometries(root: THREE.Object3D): THREE.BufferGeometry[] {
  const geos: THREE.BufferGeometry[] = [];
  root.traverse(obj => {
    const mesh = obj as THREE.Mesh;
    if (mesh.isMesh && mesh.geometry) {
      const g = mesh.geometry.clone();
      g.applyMatrix4(mesh.matrixWorld);
      geos.push(g);
    }
  });
  return geos;
}

function mergePositions(geos: THREE.BufferGeometry[], n: number, radius: number): Float32Array {
  if (geos.length === 0) return new Float32Array(n * 3);
  if (geos.length === 1) return sampleGeometry(geos[0], n, radius);
  const per = Math.floor(n / geos.length);
  const out = new Float32Array(n * 3);
  geos.forEach((g, gi) => {
    const count = gi === geos.length - 1 ? n - per * (geos.length - 1) : per;
    out.set(sampleGeometry(g, count, radius).subarray(0, count * 3), gi * per * 3);
  });
  return out;
}

/** Carga un GLTF/GLB o OBJ por URL y lo convierte en posiciones de partículas. */
export async function modelShape(n: number, radius: number, url: string): Promise<Float32Array> {
  const lower = url.toLowerCase();
  if (lower.endsWith(".obj")) {
    const obj = await new OBJLoader().loadAsync(url);
    obj.updateMatrixWorld(true);
    return mergePositions(collectGeometries(obj), n, radius);
  }
  const gltf = await new GLTFLoader().loadAsync(url);
  gltf.scene.updateMatrixWorld(true);
  return mergePositions(collectGeometries(gltf.scene), n, radius);
}
