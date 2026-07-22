/**
 * PostFX — post-procesado del núcleo.
 * Bloom (UnrealBloom via @react-three/postprocessing): hace que el centro
 * caliente y las partículas más brillantes "florezcan" con un halo suave,
 * dando la sensación cinemática de energía viva. Se lee del config en vivo,
 * así setBloom()/setGlow() de la API pública lo ajustan sin recrear nada.
 */
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { MutableRefObject } from "react";
import type { CoreConfig } from "../config/CoreConfig";

interface BloomLike {
  intensity: number;
  luminanceMaterial?: { threshold: number };
}

export function PostFX({ config }: { config: MutableRefObject<CoreConfig> }) {
  const bloomRef = useRef<BloomLike | null>(null);

  // El bloom se ajusta en vivo desde la config (API pública) sin re-montar.
  useFrame(() => {
    const b = bloomRef.current;
    if (!b) return;
    const c = config.current;
    b.intensity = c.bloom;
    if (b.luminanceMaterial) b.luminanceMaterial.threshold = c.bloomThreshold;
  });

  const c = config.current;
  return (
    <EffectComposer>
      <Bloom
        ref={bloomRef as never}
        intensity={c.bloom}
        luminanceThreshold={c.bloomThreshold}
        luminanceSmoothing={0.18}
        radius={c.bloomRadius}
        mipmapBlur
      />
    </EffectComposer>
  );
}
