import type { RGB } from "../types";
type Stop = [number, [number, number, number]];

/** Construye una paleta de 256 colores a partir de paradas [posición, [r,g,b]]. */
export function lut(stops: Stop[]): Uint8Array {
  const o = new Uint8Array(256 * 3);
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    let j = 0;
    while (j < stops.length - 2 && t > stops[j + 1][0]) j++;
    const [t0, c0] = stops[j];
    const [t1, c1] = stops[j + 1];
    const u = Math.min(1, Math.max(0, (t - t0) / (t1 - t0)));
    for (let k = 0; k < 3; k++) o[i * 3 + k] = c0[k] + (c1[k] - c0[k]) * u;
  }
  return o;
}

/** Busca el color de la paleta para un valor x (0 a 1). */
export function pal(L: Uint8Array, x: number, o: RGB): void {
  const i = (((x < 0 ? 0 : x > 1 ? 1 : x) * 255) | 0) * 3;
  o[0] = L[i] / 255;
  o[1] = L[i + 1] / 255;
  o[2] = L[i + 2] / 255;
}