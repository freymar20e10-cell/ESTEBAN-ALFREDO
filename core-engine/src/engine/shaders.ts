/**
 * Shaders del núcleo. TODO el movimiento vive en la GPU: la CPU solo
 * actualiza uniforms (números) por frame. Los buffers de posición jamás
 * se reescriben durante la animación — por eso 10k+ partículas van a 60fps.
 */
import { GLSL_SIMPLEX_3D, GLSL_CURL_3D } from "./NoiseEngine";

export const VERTEX_SHADER = /* glsl */ `
precision highp float;

attribute vec3 aFrom;      // forma de origen (morph)
attribute vec3 aTo;        // forma de destino (morph)
attribute float aSeed;     // 0..1 identidad estable de la partícula
attribute float aSize;     // variación de tamaño por partícula

uniform float uTime;
uniform float uMorph;          // progreso del morphing 0..1
uniform float uStagger;        // escalonado de llegada
uniform float uPixelRatio;
uniform float uSize;           // tamaño base
uniform float uScale;          // radio del núcleo (respiración incluida)
uniform float uSpeed;          // multiplicador de flujo
uniform float uNoiseScale;
uniform float uNoiseStrength;
uniform float uEnergy;         // 0..1 actividad del estado
uniform float uWave;           // ondas radiales (hablando)
uniform float uAudio;          // nivel de voz 0..1
uniform float uExpand;         // expansión (actualizando)
uniform float uJitter;         // inestabilidad (error)
uniform float uVortex;         // remolino agujero negro 0..1
uniform vec3  uMouse;          // posición del cursor en mundo
uniform float uMouseStrength;
uniform float uClickT;         // momento del último click (uTime)
uniform vec3  uColor;
uniform vec3  uColorHot;
uniform float uGlow;
uniform float uCoreRadius;

varying vec3 vColor;
varying float vAlpha;

${GLSL_SIMPLEX_3D}
${GLSL_CURL_3D}

float hash11(float p){ return fract(sin(p * 127.1) * 43758.5453); }

void main() {
  // ── morphing escalonado: cada partícula parte en su momento ──
  float m = clamp((uMorph * (1.0 + uStagger) - aSeed * uStagger) / max(1e-4, 1.0), 0.0, 1.0);
  m = m * m * (3.0 - 2.0 * m);
  vec3 base = mix(aFrom, aTo, m);

  // durante el tránsito, las partículas viajan por el campo de flujo
  // (arco orgánico) en vez de ir en línea recta
  float transit = sin(m * 3.14159);
  base += curlNoise(base * 0.5 + aSeed * 3.7) * transit * 0.55;

  // ── remolino (agujero negro): rotación diferencial, más rápido cerca ──
  if (uVortex > 0.001) {
    float r = length(base.xz) + 0.001;
    float ang = uVortex * uTime * (1.8 / (0.25 + r * 0.55));
    float c = cos(ang), s = sin(ang);
    base = vec3(c * base.x - s * base.z, base.y, s * base.x + c * base.z);
  }

  // ── flujo orgánico permanente (curl noise, sin aleatoriedad) ──
  float t = uTime * 0.22 * uSpeed;
  vec3 flow = curlNoise(base * uNoiseScale + vec3(0.0, t, t * 0.6));
  base += flow * uNoiseStrength * (0.5 + uEnergy);

  // ── ondas radiales al hablar ──
  float len = length(base) + 0.001;
  if (uWave > 0.001) {
    float w = sin(len * 5.5 - uTime * 7.0) * (0.35 + uAudio * 0.9);
    base += (base / len) * w * 0.09 * uWave;
  }

  // ── expansión pulsante (actualizando) ──
  if (uExpand > 0.001) {
    base *= 1.0 + uExpand * 0.16 * (0.5 + 0.5 * sin(uTime * 2.2 + len * 1.5));
  }

  // ── inestabilidad (error): vibración de alta frecuencia ──
  if (uJitter > 0.001) {
    base += (vec3(hash11(aSeed + floor(uTime * 24.0)),
                  hash11(aSeed * 2.0 + floor(uTime * 24.0)),
                  hash11(aSeed * 3.0 + floor(uTime * 24.0))) - 0.5) * 0.12 * uJitter;
  }

  // ── escala global (respiración) ──
  vec3 world = base * uScale;

  // ── interacción con el cursor: repulsión suave, nunca exagerada ──
  vec3 dm = world - uMouse;
  float md = length(dm) + 0.001;
  world += (dm / md) * exp(-md * md * 1.4) * uMouseStrength;

  // ── onda de click: un anillo que atraviesa el núcleo y se disipa ──
  float ct = uTime - uClickT;
  if (ct < 2.0) {
    float ring = sin((len - ct * 2.8) * 9.0) * exp(-ct * 2.4) * exp(-abs(len - ct * 2.8));
    world += (base / len) * ring * 0.10;
  }

  vec4 mv = modelViewMatrix * vec4(world, 1.0);
  gl_Position = projectionMatrix * mv;

  // tamaño: atenuado por distancia, con twinkle propio
  float tw = 0.75 + 0.25 * sin(uTime * (0.9 + aSeed * 2.4) + aSeed * 6.2831);
  gl_PointSize = aSize * uSize * uPixelRatio * tw * (34.0 / -mv.z);

  // color: el centro es caliente (blanco), el halo toma el color del estado
  float heat = 1.0 - smoothstep(0.0, uCoreRadius * 0.85, length(aTo));
  vColor = mix(uColor, uColorHot, heat * uGlow);
  vAlpha = (0.35 + heat * 0.65) * tw;
  // profundidad: lo lejano se desvanece un poco (volumen)
  vAlpha *= smoothstep(-16.0, -3.0, mv.z);
}
`;

export const FRAGMENT_SHADER = /* glsl */ `
precision highp float;

uniform float uOpacity;
uniform float uDim;

varying vec3 vColor;
varying float vAlpha;

void main() {
  // sprite radial suave calculado aquí mismo — sin texturas que cargar
  vec2 uv = gl_PointCoord - 0.5;
  float d = length(uv) * 2.0;
  float a = smoothstep(1.0, 0.0, d);
  a *= a;
  gl_FragColor = vec4(vColor * uDim, a * vAlpha * uOpacity * uDim);
  if (gl_FragColor.a < 0.003) discard;
}
`;
