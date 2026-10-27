import type { FilterDef } from "../types";
import { lut, pal } from "./palette";


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
