import type { MovingObject } from "@/contracts";

/**
 * Busca el objeto más cercano a unas coordenadas, dentro de una tolerancia en grados.
 * Compara contra todas las posiciones registradas del objeto (una por época) y se queda
 * con la menor distancia. Devuelve null si ninguno queda dentro de la tolerancia.
 *
 * La tolerancia por defecto es amplia (0.5°, unos 30 minutos de arco) para que el
 * usuario pueda escribir coordenadas aproximadas y aun así encuentre el candidato.
 */
export function matchObject(
  ra: number,
  dec: number,
  objects: MovingObject[],
  toleranceDeg: number = 0.5,
): MovingObject | null {
  let best: { obj: MovingObject; dist: number } | null = null;
  for (const obj of objects) {
    for (const pos of obj.positions) {
      // Diferencia de RA en -180..180 para no romper cerca de 0°/360°.
      const dRa = ((((ra - pos.ra) % 360) + 540) % 360) - 180;
      // Proyectamos la diferencia de RA por cos(dec) para que esté en grados reales.
      const dRaProj = dRa * Math.cos((pos.dec * Math.PI) / 180);
      const dDec = dec - pos.dec;
      const dist = Math.sqrt(dRaProj * dRaProj + dDec * dDec);
      if (dist <= toleranceDeg && (!best || dist < best.dist)) {
        best = { obj, dist };
      }
    }
  }
  return best?.obj ?? null;
}
