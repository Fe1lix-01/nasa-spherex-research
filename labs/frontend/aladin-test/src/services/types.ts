import type { Band, Epoch, Frame, ObjectsResponse } from "@/contracts";

/**
 * Lo que el frontend necesita pedirle al back. La versión simulada (mock) y la real (api)
 * cumplen esta misma forma, por eso se pueden intercambiar sin tocar los componentes.
 */
export interface SkyDataService {
  getEpochs(): Promise<Epoch[]>;
  getBands(): Promise<Band[]>;
  getObjects(): Promise<ObjectsResponse>;
  getFrames(): Promise<Frame[]>;
}
