import type { FilterId } from "@/features/viewer/types";

/**
 * Aproximación de color de cada filtro del visor para el mosaico de Aladin.
 *
 * Los filtros reales trabajan píxel por píxel sobre las imágenes de la prueba. El mosaico lo
 * dibuja Aladin con WebGL, así que aquí solo se imita el tono con filtros CSS. Es una
 * ayuda visual, no una banda real.
 */
type Recipe = { gray: number; sepia: number; hue: number; sat: number; contrast: number };

const RECIPES: Record<FilterId, Recipe> = {
  visible: { gray: 0, sepia: 0, hue: 0, sat: 1, contrast: 1 },
  nir: { gray: 1, sepia: 1, hue: -12, sat: 2.2, contrast: 1.05 }, // naranja cálido
  mir: { gray: 0.3, sepia: 0.7, hue: -45, sat: 2, contrast: 1.05 }, // rojizo
  ice: { gray: 1, sepia: 1, hue: 150, sat: 3, contrast: 1.05 }, // cian
  thermal: { gray: 1, sepia: 1, hue: -35, sat: 4, contrast: 1.2 }, // rojo-naranja intenso
  comp: { gray: 0, sepia: 0, hue: 0, sat: 2.2, contrast: 1.1 }, // colores realzados
};

/**
 * @param inten "Aplicación del filtro" (0 a 100): cuánto se acerca al tono del filtro.
 * @param gain "Intensidad de luz" (10 a 300): brillo general.
 */
export function skyCssFilter(id: FilterId, inten: number, gain: number): string {
  const r = RECIPES[id];
  const k = Math.min(Math.max(inten, 0), 100) / 100;
  const mix = (neutral: number, target: number) => neutral + (target - neutral) * k;

  const parts: string[] = [];
  if (r.gray) parts.push(`grayscale(${mix(0, r.gray).toFixed(2)})`);
  if (r.sepia) parts.push(`sepia(${mix(0, r.sepia).toFixed(2)})`);
  if (r.hue) parts.push(`hue-rotate(${mix(0, r.hue).toFixed(0)}deg)`);
  if (r.sat !== 1) parts.push(`saturate(${mix(1, r.sat).toFixed(2)})`);
  if (r.contrast !== 1) parts.push(`contrast(${mix(1, r.contrast).toFixed(2)})`);
  parts.push(`brightness(${(gain / 100).toFixed(2)})`);
  return parts.join(" ");
}
