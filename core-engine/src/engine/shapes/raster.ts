/**
 * Formas rasterizadas: TEXTO y SVG convertidos a partículas.
 * Técnica: se dibuja en un canvas 2D fuera de pantalla, se leen los píxeles
 * y las partículas se colocan sobre los píxeles encendidos. Sirve para
 * palabras (JARVIS, ONLINE...) y para cualquier logo vectorial.
 */

interface RasterOptions {
  radius: number;
  /** Profundidad del extrusionado en z (0 = plano). */
  depth?: number;
}

function sampleCanvas(
  n: number,
  draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void,
  { radius, depth = 0.12 }: RasterOptions,
): Float32Array {
  const W = 480, H = 240;
  const canvas = document.createElement("canvas");
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#fff";
  draw(ctx, W, H);

  const img = ctx.getImageData(0, 0, W, H).data;
  const lit: number[] = [];
  for (let y = 0; y < H; y += 1) {
    for (let x = 0; x < W; x += 1) {
      if (img[(y * W + x) * 4 + 3] > 96) lit.push(x, y);
    }
  }

  const p = new Float32Array(n * 3);
  if (lit.length === 0) return p;   // dibujo vacío: todas al centro
  const pixels = lit.length / 2;
  const scale = (radius * 2.6) / W;
  for (let i = 0; i < n; i++) {
    const k = (Math.floor(Math.random() * pixels)) * 2;
    const x = lit[k] + Math.random() - 0.5;
    const y = lit[k + 1] + Math.random() - 0.5;
    p[i * 3] = (x - W / 2) * scale;
    p[i * 3 + 1] = -(y - H / 2) * scale;
    p[i * 3 + 2] = (Math.random() - 0.5) * depth * radius;
  }
  return p;
}

/** Texto → partículas. Uso: generate('text', n, { radius, text: 'JARVIS' }) */
export function textShape(n: number, radius: number, text: string): Float32Array {
  return sampleCanvas(n, (ctx, w, h) => {
    let size = 150;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    do {
      ctx.font = `700 ${size}px 'Bahnschrift','Segoe UI',sans-serif`;
      size -= 6;
    } while (ctx.measureText(text).width > w * 0.92 && size > 18);
    ctx.fillText(text, w / 2, h / 2);
  }, { radius });
}

/** SVG (contenido del archivo) → partículas. El SVG se pinta y se muestrea. */
export function svgShape(n: number, radius: number, svgMarkup: string): Promise<Float32Array> {
  return new Promise((resolve) => {
    const blob = new Blob([svgMarkup], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      const out = sampleCanvas(n, (ctx, w, h) => {
        const s = Math.min((w * 0.9) / img.width, (h * 0.9) / img.height);
        ctx.drawImage(img, (w - img.width * s) / 2, (h - img.height * s) / 2, img.width * s, img.height * s);
      }, { radius });
      URL.revokeObjectURL(url);
      resolve(out);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(new Float32Array(n * 3)); };
    img.src = url;
  });
}
