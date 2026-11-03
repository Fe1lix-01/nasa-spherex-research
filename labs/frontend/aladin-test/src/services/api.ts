import type { Band, Epoch, Frame, ObjectsResponse } from "@/contracts";
import type { SkyDataService } from "./types";

// URL base del back. Se define en .env.local como NEXT_PUBLIC_API_URL.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) throw new Error(`Error ${res.status} al pedir ${path}`);
  return (await res.json()) as T;
}

// Las rutas son una PROPUESTA: hay que acordarlas con el back.
export const apiService: SkyDataService = {
  getEpochs: () => getJson<Epoch[]>("/epochs"),
  getBands: () => getJson<Band[]>("/bands"),
  getObjects: () => getJson<ObjectsResponse>("/objects"),
  getFrames: () => getJson<Frame[]>("/frames"),
};
