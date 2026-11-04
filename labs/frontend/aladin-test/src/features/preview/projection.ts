import type { Frame } from "@/contracts";

/**
 * Convierte RA/Dec a coordenadas dentro de la imagen, de 0 a 1 en cada eje.
 *
 * Aproximación plana: sirve para campos de pocos grados. Convención habitual en astronomía:
 * norte arriba y este a la izquierda (por eso RA crece hacia la izquierda).
 * Devuelve null si el punto cae fuera de la imagen.
 *
 * TODO: reemplazar por el WCS real del FITS cuando el script exporte la cabecera.
 */
export function skyToImage(ra: number, dec: number, frame: Frame): { x: number; y: number } | null {
  // Diferencia de RA en -180..180, para no romper cerca de 0°/360°.
  const dRa = ((((ra - frame.ra) % 360) + 540) % 360) - 180;
  const x = 0.5 - (dRa * Math.cos((frame.dec * Math.PI) / 180)) / frame.fovDeg;
  const y = 0.5 - (dec - frame.dec) / frame.fovDeg;
  if (x < 0 || x > 1 || y < 0 || y > 1) return null;
  return { x, y };
}
