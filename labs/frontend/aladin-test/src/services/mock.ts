import type { Band, Frame, ObjectsResponse } from "@/contracts";
import epochsJson from "@/mocks/epochs.json";
import framesJson from "@/mocks/frames.json";
import objectsJson from "@/mocks/objects.json";
import type { SkyDataService } from "./types";

/** Simula el tiempo de respuesta de una red, para poder probar los estados de "cargando". */
const NETWORK_DELAY_MS = 300;
const delay = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// Ilustrativo: 102 bandas repartidas de forma uniforme entre 0.75 y 5.0 µm.
// Los rangos reales vendrán del back y no tienen por qué ser uniformes.
const BAND_COUNT = 102;
const WAVELENGTH_MIN_UM = 0.75;
const WAVELENGTH_MAX_UM = 5.0;

const round = (n: number) => Number(n.toFixed(4));

function makeBands(): Band[] {
  const step = (WAVELENGTH_MAX_UM - WAVELENGTH_MIN_UM) / BAND_COUNT;
  return Array.from({ length: BAND_COUNT }, (_, i) => ({
    index: i + 1,
    wavelengthMinUm: round(WAVELENGTH_MIN_UM + i * step),
    wavelengthMaxUm: round(WAVELENGTH_MIN_UM + (i + 1) * step),
  }));
}

export const mockService: SkyDataService = {
  async getEpochs() {
    await delay(NETWORK_DELAY_MS);
    return epochsJson;
  },
  async getBands() {
    await delay(NETWORK_DELAY_MS);
    return makeBands();
  },
  async getObjects() {
    await delay(NETWORK_DELAY_MS);
    // TypeScript infiere "kind" como string al leer el JSON; aquí lo declaramos como
    // ObjectKind. Cuando llegue el back real conviene validar la forma con Zod.
    return objectsJson as unknown as ObjectsResponse;
  },
  async getFrames() {
    await delay(NETWORK_DELAY_MS);
    return framesJson as Frame[];
  },
};
