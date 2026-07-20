/**
 * InteractionEngine — mouse, hover, click y arrastre.
 * El cursor se proyecta al plano del núcleo y viaja como uniform al shader
 * (repulsión sutil). El arrastre rota el pivote con inercia. El click
 * dispara una onda que atraviesa las partículas y se disipa.
 */
import * as THREE from "three";

export class InteractionEngine {
  /** Posición del cursor en coordenadas de mundo (plano z=0). */
  readonly mouseWorld = new THREE.Vector3(999, 999, 999);
  /** Momento (tiempo del reloj del motor) del último click. */
  clickTime = -10;

  rotX = 0.1;
  rotY = 0;
  private velX = 0;
  private velY = 0;
  private dragging = false;
  private draggedDistance = 0;
  private lastX = 0;
  private lastY = 0;

  private raycaster = new THREE.Raycaster();
  private plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  private ndc = new THREE.Vector2();

  attach(el: HTMLElement, camera: THREE.Camera, getTime: () => number): () => void {
    el.style.touchAction = "none";
    el.style.cursor = "grab";

    const toNdc = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      this.ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    };

    const onMove = (e: PointerEvent) => {
      toNdc(e);
      this.raycaster.setFromCamera(this.ndc, camera);
      this.raycaster.ray.intersectPlane(this.plane, this.mouseWorld);
      if (this.dragging) {
        const dx = e.clientX - this.lastX, dy = e.clientY - this.lastY;
        this.lastX = e.clientX; this.lastY = e.clientY;
        this.draggedDistance += Math.abs(dx) + Math.abs(dy);
        this.rotY += dx * 0.006;
        this.rotX = THREE.MathUtils.clamp(this.rotX + dy * 0.006, -1.2, 1.2);
        this.velY = dx * 0.006; this.velX = dy * 0.006;
      }
    };
    const onDown = (e: PointerEvent) => {
      this.dragging = true; this.draggedDistance = 0;
      this.lastX = e.clientX; this.lastY = e.clientY;
      this.velX = this.velY = 0;
      el.style.cursor = "grabbing";
      el.setPointerCapture(e.pointerId);
    };
    const onUp = (e: PointerEvent) => {
      if (this.dragging && this.draggedDistance < 6) this.clickTime = getTime();  // click real, no arrastre
      this.dragging = false;
      el.style.cursor = "grab";
      try { el.releasePointerCapture(e.pointerId); } catch { /* ya liberado */ }
    };
    const onLeave = () => this.mouseWorld.set(999, 999, 999);

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerdown", onDown);
    el.addEventListener("pointerup", onUp);
    el.addEventListener("pointercancel", onUp);
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerdown", onDown);
      el.removeEventListener("pointerup", onUp);
      el.removeEventListener("pointercancel", onUp);
      el.removeEventListener("pointerleave", onLeave);
    };
  }

  /** Aplica inercia y auto-rotación. Llamar cada frame. */
  update(pivot: THREE.Object3D, autoRotate: number, energy: number): void {
    if (!this.dragging) {
      this.rotY += this.velY; this.rotX += this.velX;
      this.velX *= 0.94; this.velY *= 0.94;
      this.rotX = THREE.MathUtils.clamp(this.rotX, -1.2, 1.2);
      if (Math.abs(this.velX) + Math.abs(this.velY) < 0.0005) {
        this.rotY += autoRotate * (1 + energy * 1.5) * 0.016;
      }
    }
    pivot.rotation.set(this.rotX, this.rotY, 0);
  }
}
