import type { Frame } from "@/contracts";
import { H, W } from "@/features/viewer/constants";

/**
 * Convierte RA/Dec a la posición en el canvas del visor, de 0 a 1 en cada eje.
 *
 * El visor dibuja la imagen cuadrada en un lienzo de W×H con recorte tipo "cover":
 * la imagen se escala para llenar el ancho y se recorta arriba y abajo. Por eso hay
 * que tomar en cuenta ese recorte al ubicar el punto.
 *
 * Convención astronómica: norte arriba y este a la izquierda (RA crece hacia la izquierda).
 * Aproximación plana, válida para campos de pocos grados.
 * Devuelve null si el punto cae fuera de la imagen.
 *
 * TODO: reemplazar por el WCS real del FITS cuando el script exporte la cabecera.
 */
export function skyToImage(ra: number, dec: number, frame: Frame): { x: number; y: number } | null {
  // Diferencia de RA en -180..180, para no romper cerca de 0°/360°.
  const dRa = ((((ra - frame.ra) % 360) + 540) % 360) - 180;
  // Posición dentro de la imagen cuadrada, de 0 a 1.
  const xImg = 0.5 - (dRa * Math.cos((frame.dec * Math.PI) / 180)) / frame.fovDeg;
  const yImg = 0.5 - (dec - frame.dec) / frame.fovDeg;
  if (xImg < 0 || xImg > 1 || yImg < 0 || yImg > 1) return null;

  // Recorte "cover": la imagen mide W×W en el lienzo, y solo se ve la franja central de H.
  const visibleFrac = H / W; // fracción visible de la imagen en vertical
  const cropTop = (1 - visibleFrac) / 2; // fracción recortada arriba
  const x = xImg;
  const y = (yImg - cropTop) / visibleFrac;
  if (y < 0 || y > 1) return null; // cae en la parte recortada
  return { x, y };
}
