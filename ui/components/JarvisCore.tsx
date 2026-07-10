import { useEffect, useRef } from "react";
import * as THREE from "three";
import { generateShape, type ShapeId } from "@/lib/jarvis-shapes";
import { STATES, type JarvisState } from "@/lib/jarvis-states";

interface JarvisCoreProps {
  state: JarvisState;
  shape: ShapeId;
  /** 0..1 extra parameter (e.g. "mass" for a black hole / scale of the shape) */
  intensity?: number;
  count?: number;
  className?: string;
}

export function JarvisCore({
  state,
  shape,
  intensity = 0.5,
  count = 6000,
  className,
}: JarvisCoreProps) {
  const mountRef = useRef<HTMLDivElement>(null);

  // live refs so we can update the render loop without re-creating the scene
  const stateRef = useRef(state);
  const shapeRef = useRef(shape);
  const intensityRef = useRef(intensity);
  stateRef.current = state;
  shapeRef.current = shape;
  intensityRef.current = intensity;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const width = mount.clientWidth || 600;
    const height = mount.clientHeight || 600;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.z = 7;

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    // Buffers: current, source (morph from), target (morph to)
    const current = generateShape(shapeRef.current, count);
    const target = generateShape(shapeRef.current, count);
    const source = current.slice();
    // per-particle random offset for organic motion
    const seeds = new Float32Array(count);
    for (let i = 0; i < count; i++) seeds[i] = Math.random();

    // Per-particle colors: each particle is independent and gets its own
    // hue jitter around the current state color so the core looks "alive".
    // colors      = live buffer sent to the GPU
    // colorSource = color we are morphing FROM
    // colorTarget = color we are morphing TO (state color + per-particle jitter)
    const colors = new Float32Array(count * 3);
    const colorSource = new Float32Array(count * 3);
    const colorTarget = new Float32Array(count * 3);
    // per-particle hue/brightness variation, stable across the particle's life
    const hueJitter = new Float32Array(count);
    const briJitter = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      hueJitter[i] = (Math.random() - 0.5) * 0.12; // +-hue shift
      briJitter[i] = 0.75 + Math.random() * 0.5; // brightness multiplier
    }

    const tmpColor = new THREE.Color();
    const baseHSL = { h: 0, s: 0, l: 0 };

    const fillColorTarget = (rgb: [number, number, number]) => {
      tmpColor.setRGB(rgb[0], rgb[1], rgb[2]);
      tmpColor.getHSL(baseHSL);
      for (let i = 0; i < count; i++) {
        const h = (baseHSL.h + hueJitter[i] + 1) % 1;
        const l = Math.min(1, Math.max(0.15, baseHSL.l * briJitter[i]));
        tmpColor.setHSL(h, Math.min(1, baseHSL.s + 0.1), l);
        colorTarget[i * 3] = tmpColor.r;
        colorTarget[i * 3 + 1] = tmpColor.g;
        colorTarget[i * 3 + 2] = tmpColor.b;
      }
    };

    fillColorTarget(STATES[stateRef.current].color);
    colors.set(colorTarget);
    colorSource.set(colorTarget);
    let colorMix = 1; // 1 = fully at colorTarget

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(current, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    // circular soft sprite
    const sprite = makeParticleTexture();
    const material = new THREE.PointsMaterial({
      size: 0.055,
      map: sprite,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexColors: true,
    });

    // pivot group so the whole core can be freely rotated (inspected) by drag
    const pivot = new THREE.Group();
    scene.add(pivot);

    const points = new THREE.Points(geometry, material);
    pivot.add(points);

    // faint core glow
    const glowGeo = new THREE.SphereGeometry(0.6, 32, 32);
    const glowMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(...STATES[stateRef.current].color),
      transparent: true,
      opacity: 0.12,
      blending: THREE.AdditiveBlending,
    });
    const glow = new THREE.Mesh(glowGeo, glowMat);
    pivot.add(glow);

    // ---- inspect / orbit rotation controls ----
    // rotX / rotY are the user-controlled orientation; when idle the core
    // keeps a gentle auto-spin. Dragging overrides and adds momentum.
    let rotX = 0;
    let rotY = 0;
    let velX = 0;
    let velY = 0;
    let dragging = false;
    let lastPX = 0;
    let lastPY = 0;
    let lastMoveT = 0;

    const el = renderer.domElement;
    el.style.touchAction = "none";
    el.style.cursor = "grab";

    const onPointerDown = (e: PointerEvent) => {
      dragging = true;
      lastPX = e.clientX;
      lastPY = e.clientY;
      velX = 0;
      velY = 0;
      el.style.cursor = "grabbing";
      el.setPointerCapture(e.pointerId);
    };
    const onPointerMove = (e: PointerEvent) => {
      if (!dragging) return;
      const dx = e.clientX - lastPX;
      const dy = e.clientY - lastPY;
      lastPX = e.clientX;
      lastPY = e.clientY;
      rotY += dx * 0.008;
      rotX += dy * 0.008;
      // clamp vertical so it doesn't flip over completely
      rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
      velY = dx * 0.008;
      velX = dy * 0.008;
      lastMoveT = performance.now();
    };
    const onPointerUp = (e: PointerEvent) => {
      dragging = false;
      el.style.cursor = "grab";
      try {
        el.releasePointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
      // if the pointer stopped before release, kill momentum
      if (performance.now() - lastMoveT > 80) {
        velX = 0;
        velY = 0;
      }
    };
    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerup", onPointerUp);
    el.addEventListener("pointercancel", onPointerUp);

    let morph = 1; // 1 = fully at target
    let lastShape = shapeRef.current;
    let lastState = stateRef.current;
    const glowColor = new THREE.Color(...STATES[stateRef.current].color);

    let raf = 0;
    const clock = new THREE.Clock();

    const tick = () => {
      const t = clock.getElapsedTime();
      const style = STATES[stateRef.current];

      // detect shape change -> start morph
      if (shapeRef.current !== lastShape) {
        source.set(current);
        target.set(generateShape(shapeRef.current, count));
        lastShape = shapeRef.current;
        morph = 0;
      }
      if (morph < 1) morph = Math.min(1, morph + 0.02);

      // detect state change -> start color morph
      if (stateRef.current !== lastState) {
        colorSource.set(colors);
        fillColorTarget(style.color);
        lastState = stateRef.current;
        colorMix = 0;
      }
      if (colorMix < 1) colorMix = Math.min(1, colorMix + 0.03);

      const ease = morph * morph * (3 - 2 * morph); // smoothstep
      const breath = 1 + Math.sin(t * style.breathSpeed) * style.breathAmp;
      const scale = breath * (0.7 + intensityRef.current * 0.6);
      const energy = style.energy;

      const arr = geometry.attributes.position.array as Float32Array;
      const cArr = geometry.attributes.color.array as Float32Array;
      // subtle per-particle shimmer so each dot feels alive
      const shimmer = 0.9 + Math.sin(t * 2) * 0.1;
      for (let i = 0; i < count; i++) {
        const ix = i * 3;
        const seed = seeds[i];
        // interpolate source -> target
        const bx = source[ix] + (target[ix] - source[ix]) * ease;
        const by = source[ix + 1] + (target[ix + 1] - source[ix + 1]) * ease;
        const bz = source[ix + 2] + (target[ix + 2] - source[ix + 2]) * ease;
        // organic turbulence
        const wob = Math.sin(t * (1 + seed) + seed * 6.28) * 0.06 * energy;
        arr[ix] = bx * scale + wob;
        arr[ix + 1] = by * scale + Math.cos(t * (0.8 + seed) + seed * 3.14) * 0.06 * energy;
        arr[ix + 2] = bz * scale + wob;

        // per-particle color morph + gentle twinkle
        const tw = 0.85 + Math.sin(t * (1.5 + seed * 2) + seed * 6.28) * 0.15;
        const cm = colorMix;
        cArr[ix] = (colorSource[ix] + (colorTarget[ix] - colorSource[ix]) * cm) * tw * shimmer;
        cArr[ix + 1] = (colorSource[ix + 1] + (colorTarget[ix + 1] - colorSource[ix + 1]) * cm) * tw * shimmer;
        cArr[ix + 2] = (colorSource[ix + 2] + (colorTarget[ix + 2] - colorSource[ix + 2]) * cm) * tw * shimmer;
      }
      geometry.attributes.position.needsUpdate = true;
      geometry.attributes.color.needsUpdate = true;

      // glow follows the state color
      const target3 = style.color;
      glowColor.lerp(new THREE.Color(target3[0], target3[1], target3[2]), 0.06);
      glowMat.color.copy(glowColor);
      glowMat.opacity = 0.1 + Math.sin(t * style.breathSpeed) * 0.05 + energy * 0.05;

      // ---- orientation: user drag + inertia, gentle auto-spin when idle ----
      if (!dragging) {
        // apply momentum, then decay it
        rotY += velY;
        rotX += velX;
        velX *= 0.94;
        velY *= 0.94;
        rotX = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, rotX));
        // resume a slow ambient spin once momentum has faded
        const idle = Math.abs(velX) + Math.abs(velY) < 0.0005;
        if (idle) rotY += 0.0012 + energy * 0.001;
      }
      pivot.rotation.y = rotY;
      pivot.rotation.x = rotX;
      // internal particle life keeps its own subtle bob
      points.rotation.x = Math.sin(t * 0.15) * 0.05;

      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    tick();

    const onResize = () => {
      const w = mount.clientWidth || 600;
      const h = mount.clientHeight || 600;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      el.removeEventListener("pointerdown", onPointerDown);
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("pointercancel", onPointerUp);
      geometry.dispose();
      material.dispose();
      sprite.dispose();
      glowGeo.dispose();
      glowMat.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [count]);

  return <div ref={mountRef} className={className} />;
}

function makeParticleTexture(): THREE.Texture {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const g = ctx.createRadialGradient(
    size / 2, size / 2, 0,
    size / 2, size / 2, size / 2,
  );
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.25, "rgba(255,255,255,0.85)");
  g.addColorStop(0.55, "rgba(255,255,255,0.25)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.Texture(canvas);
  tex.needsUpdate = true;
  return tex;
}
