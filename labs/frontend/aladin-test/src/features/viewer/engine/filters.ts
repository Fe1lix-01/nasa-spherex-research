import type { FilterDef, RGB } from "../types";
type Stop = [number, [number, number, number]];

/** Construye una paleta de 256 colores a partir de paradas [posición, [r,g,b]]. */
function lut(stops: Stop[]): Uint8Array {
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
function pal(L: Uint8Array, x: number, o: RGB): void {
  const i = (((x < 0 ? 0 : x > 1 ? 1 : x) * 255) | 0) * 3;
  o[0] = L[i] / 255;
  o[1] = L[i + 1] / 255;
  o[2] = L[i + 2] / 255;
}

const L_NIR = lut([
  [0, [0, 0, 0]],
  [0.35, [90, 30, 5]],
  [0.7, [255, 150, 40]],
  [1, [255, 240, 200]],
]);
const L_ICE = lut([
  [0, [0, 0, 10]],
  [0.4, [10, 60, 110]],
  [0.75, [80, 220, 255]],
  [1, [240, 255, 255]],
]);
const L_THM = lut([
  [0, [0, 0, 4]],
  [0.25, [66, 10, 104]],
  [0.5, [187, 55, 84]],
  [0.75, [249, 142, 9]],
  [1, [252, 255, 164]],
]);

export const FILTERS: FilterDef[] = [
  {
    id: "visible",
    name: "Visible",
    band: "0.38–0.75 µm",
    desc: "Referencia óptica: una aproximación al cielo que percibe el ojo humano.",
    fn: null,
  },
  {
    id: "nir",
    name: "IR cercano",
    band: "0.75–2.5 µm",
    desc: "Sugiere estrellas y regiones ocultas tras el polvo.",
    fn: (_v, _n, ir, _t, _ic, o) => pal(L_NIR, ir, o),
  },
  {
    id: "mir",
    name: "IR medio",
    band: "2.5–5 µm",
    desc: "Evoca polvo cálido y señales moleculares. Solo un tramo orientativo del IR medio.",
    fn: (v, n, ir, _t, _ic, o) => {
      o[0] = ir * 1.15;
      o[1] = ir * 0.45 + v * 0.55;
      o[2] = v * 0.9 + n * 0.2;
    },
  },
  {
    id: "ice",
    name: "Hielos",
    band: "2.7–4.8 µm",
    desc: "Realce ilustrativo de bandas asociadas a hielos. No identifica moléculas.",
    fn: (v, _n, _ir, _t, ic, o) => {
      pal(L_ICE, ic, o);
      o[0] += v * 0.25;
      o[1] += v * 0.25;
      o[2] += v * 0.25;
    },
  },
  {
    id: "thermal",
    name: "Térmico",
    band: "8–14 µm",
    desc: "Fuera de SPHEREx. Representación de emisión térmica, no temperatura medida.",
    fn: (_v, _n, _ir, t, _ic, o) => pal(L_THM, t, o),
  },
  {
    id: "comp",
    name: "Compuesto",
    band: "varias bandas",
    desc: "Superpone varias bandas en un solo falso color (rojo = térmico, verde = IR, azul = visible). Composición ilustrativa.",
    fn: (v, n, ir, t, _ic, o) => {
      o[0] = t * 1.1;
      o[1] = ir * 0.95;
      o[2] = v + n * 0.2;
    },
  },
];
