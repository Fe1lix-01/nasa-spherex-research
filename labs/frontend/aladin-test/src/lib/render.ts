import { N } from "./constants";
import type { FilterDef, Layers, RGB } from "./types";

const out: RGB = [0, 0, 0];

// Tabla de exposición: evita calcular Math.exp tres veces por píxel.
// Cubre valores de luz de 0 a 4 en pasos de 1/256.
const TONE_SCALE = 256;
const TONE_MAX = 4 * TONE_SCALE;
const tone = new Float32Array(TONE_MAX + 1);

/**
 * Dibuja las capas en el lienzo.
 * - `inten` (0–100): cuánto se aplica el filtro sobre la vista visible.
 * - `gain` (10–300): intensidad de la luz (exposición).
 */
export function renderLayers(
  ctx: CanvasRenderingContext2D,
  image: ImageData,
  L: Layers,
  filter: FilterDef,
  inten: number,
  gain: number
): void {
  const d = image.data;
  const fn = filter.fn;
  const k = fn ? inten / 100 : 0;
  const g = (gain / 100) * 1.8;

  for (let i = 0; i <= TONE_MAX; i++) {
    tone[i] = 255 * (1 - Math.exp(-(i / TONE_SCALE) * g));
  }
  const idx = (x: number): number => {
    const j = (x * TONE_SCALE) | 0;
    return j < 0 ? 0 : j > TONE_MAX ? TONE_MAX : j;
  };

  for (let i = 0, p = 0; i < N; i++, p += 4) {
    const v = L.v[i];
    const n = L.neb[i];

    // vista visible
    let r = v + n * 0.35;
    let gg = v * 0.92 + n * 0.08;
    let b = v + n * 0.15;

    // mezcla con el filtro
    if (fn && k > 0) {
      fn(v, n, L.ir[i], L.th[i], L.ice[i], out);
      r += (out[0] - r) * k;
      gg += (out[1] - gg) * k;
      b += (out[2] - b) * k;
    }

    d[p] = tone[idx(r)];
    d[p + 1] = tone[idx(gg)];
    d[p + 2] = tone[idx(b)];
    d[p + 3] = 255;
  }
  ctx.putImageData(image, 0, 0);
}
