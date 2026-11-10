
/**
 * Cliente HTTP para consumir los endpoints reales de ETER API.
 *
 * Este servicio es independiente de mockService y skyData.
 * Permite consultar el catálogo astronómico, los FITS,
 * las imágenes PNG y las observaciones.
 */

import type {
  FramesResponse,
  ObjectsResponse,
  AstronomicalObjectDetail,
  ObservationsResponse,
} from "@/contracts/api";

/**
 * Dirección base del backend.
 *
 * Si existe NEXT_PUBLIC_API_URL, se utiliza esa dirección.
 * De lo contrario, se conecta al backend local de FastAPI.
 */
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

/**
 * Obtiene un mensaje legible cuando el backend devuelve un error.
 */
async function getApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as {
      detail?: unknown;
    };

    if (typeof payload.detail === "string") {
      return payload.detail;
    }

    if (payload.detail !== undefined) {
      return JSON.stringify(payload.detail);
    }
  } catch {
    // Si la respuesta no contiene JSON, se utiliza el error HTTP.
  }

  return `La API respondió con HTTP ${response.status}.`;
}

/**
 * Ejecuta una petición GET y valida el estado HTTP.
 *
 * El tipo genérico permite especificar el contrato esperado
 * para cada endpoint.
 */
async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await getApiError(response);
    throw new Error(message);
  }

  return (await response.json()) as T;
}

/**
 * Funciones disponibles para consultar ETER API.
 *
 * Todos los métodos permanecen dentro de este único objeto.
 */
export const eterApiService = {
  /**
   * Obtiene los metadatos de todos los frames FITS.
   */
  getFrames(): Promise<FramesResponse> {
    return request<FramesResponse>("/frames");
  },

  /**
   * Construye la URL de la imagen PNG de un frame.
   *
   * El backend devuelve directamente la imagen,
   * por lo que no es necesario procesarla como JSON.
   */
  getFrameImageUrl(frameId: string): string {
    return `${API_BASE_URL}/frames/${encodeURIComponent(frameId)}/image`;
  },

  /**
   * Obtiene el catálogo de objetos.
   * Permite filtrar por nombre mediante el parámetro q.
   */
  getObjects(query?: string): Promise<ObjectsResponse> {
    const params = new URLSearchParams();
    const normalizedQuery = query?.trim();

    if (normalizedQuery) {
      params.set("q", normalizedQuery);
    }

    const queryString = params.toString();
    const path = queryString
      ? `/objects?${queryString}`
      : "/objects";

    return request<ObjectsResponse>(path);
  },

  /**
   * Obtiene la información completa de un objeto,
   * incluyendo sus observaciones.
   */
  getObject(id: string): Promise<AstronomicalObjectDetail> {
    return request<AstronomicalObjectDetail>(
      `/objects/${encodeURIComponent(id)}`
    );
  },

  /**
   * Obtiene todas las observaciones disponibles.
   */
  getObservations(): Promise<ObservationsResponse> {
    return request<ObservationsResponse>("/observations");
  },
};
