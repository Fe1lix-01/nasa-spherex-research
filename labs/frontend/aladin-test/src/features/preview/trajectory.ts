import type { Epoch, MovingObject } from "@/contracts";

export type SkyPoint = { ra: number; dec: number };

/** Puntos medidos del objeto, ordenados por época, con el índice de la época (0, 1, 2…). */
export function trackPoints(obj: MovingObject, epochs: Epoch[]): (SkyPoint & { index: number })[] {
  const index = new Map(epochs.map((e, i) => [e.id, i]));
  const pts: (SkyPoint & { index: number })[] = [];
  for (const p of obj.positions) {
    const i = index.get(p.epochId);
    if (i !== undefined) pts.push({ index: i, ra: p.ra, dec: p.dec });
  }
  return pts.sort((a, b) => a.index - b.index);
}

/**
 * Posición del objeto en el instante t (0 = primera época, 1 = segunda…).
 * Entre dos detecciones interpola en línea recta; si en alguna época no se detectó,
 * simplemente "salta" esa y une las que sí tiene. Fuera del rango se queda en el extremo.
 */
export function positionAt(obj: MovingObject, epochs: Epoch[], t: number): SkyPoint | null {
  const pts = trackPoints(obj, epochs);
  if (pts.length === 0) return null;
  const first = pts[0];
  const end = pts[pts.length - 1];
  if (t <= first.index) return { ra: first.ra, dec: first.dec };
  if (t >= end.index) return { ra: end.ra, dec: end.dec };

  for (let k = 0; k < pts.length - 1; k++) {
    const a = pts[k];
    const b = pts[k + 1];
    if (t >= a.index && t <= b.index) {
      const f = (t - a.index) / (b.index - a.index);
      // Diferencia de RA en -180..180 para no romper cerca de 0°/360°.
      const dRa = ((((b.ra - a.ra) % 360) + 540) % 360) - 180;
      return { ra: a.ra + dRa * f, dec: a.dec + (b.dec - a.dec) * f };
    }
  }
  return { ra: end.ra, dec: end.dec };
}

/** Fecha (YYYY-MM-DD) en el instante t, interpolando entre las fechas de las épocas. */
export function dateAt(epochs: Epoch[], t: number): string {
  if (epochs.length === 0) return "";
  const i = Math.min(Math.max(Math.floor(t), 0), epochs.length - 1);
  const j = Math.min(i + 1, epochs.length - 1);
  const a = new Date(epochs[i].observedAt).getTime();
  const b = new Date(epochs[j].observedAt).getTime();
  const f = Math.min(Math.max(t - i, 0), 1);
  return new Date(a + (b - a) * f).toISOString().slice(0, 10);
}
