import type { Epoch, MovingObject } from "@/contracts";

export type SkyPoint = { ra: number; dec: number };

/** Un punto de la trayectoria, en el orden cronológico en que viene guardado. */
export type TrackPoint = SkyPoint & {
  index: number;
  imageUrl?: string;
  fovDeg?: number;
  observedAt?: string;
};

/**
 * Puntos medidos del objeto, en el orden en que vienen en `positions` (ya es el orden
 * cronológico: así los guarda cada fuente de datos, simulada o real).
 */
export function trackPoints(obj: MovingObject): TrackPoint[] {
  return obj.positions.map((p, index) => ({
    index,
    ra: p.ra,
    dec: p.dec,
    imageUrl: p.imageUrl,
    fovDeg: p.fovDeg,
    observedAt: p.observedAt,
  }));
}

/**
 * Posición del objeto en el instante t (0 = primera posición, 1 = segunda…).
 * Entre dos puntos interpola en línea recta; fuera del rango se queda en el extremo.
 */
export function positionAt(obj: MovingObject, t: number): SkyPoint | null {
  const pts = trackPoints(obj);
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

/**
 * true cuando el objeto trae su propia imagen en CADA posición: es un candidato con datos
 * reales (como Barnard), no uno de los 3 objetos simulados que comparten las imágenes del
 * recuadro "Prueba".
 */
export function hasOwnImages(obj: MovingObject): boolean {
  return obj.positions.length > 0 && obj.positions.every((p) => !!p.imageUrl);
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

/**
 * Lista de "épocas" a mostrar para este objeto: si trae sus propias fechas (datos reales),
 * una por cada una de sus posiciones; si no, las épocas compartidas (objetos simulados).
 */
export function epochsForObject(obj: MovingObject | null, sharedEpochs: Epoch[]): Epoch[] {
  if (!obj) return sharedEpochs;
  const pts = trackPoints(obj);
  if (pts.length > 0 && pts.every((p) => p.observedAt)) {
    return pts.map((p, i) => ({
      id: `e${i + 1}`,
      observedAt: p.observedAt as string,
      label: `Época ${i + 1}`,
    }));
  }
  return sharedEpochs;
}
