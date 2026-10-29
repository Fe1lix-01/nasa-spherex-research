import type {                                                    // Cliente que se comunica con FastAPI //
  AstronomicalObjectDetail,                            // Impotacion del catalogo y los detalles de los objetos //
  ObjectsResponse,
} from "./types";

const API_BASE_URL = (                               // Definicion de la dirrecion del backend //
  process.env.NEXT_PUBLIC_ETER_API_URL ??            //Intenta leer la variable de entorno //
  "http://127.0.0.1:8000"                            //Es la direccion predeterminada el backend local //
).replace(/\/$/, "");

async function request<T>(path: string): Promise<T> {    // Trabaja de forma asincrona esperando el resultado sin bloquear la app
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {  // Envia una peticion HTTP al Backend //
      cache: "no-store",                                // Evita reutilizar una respuesta almacenada en cache //
    });
  } catch {
    throw new Error(                                   // Errores 404 o 500 no entran en este catch//
      "No se pudo conectar con el backend de ÉTER."
    );
  }

  if (!response.ok) {                                 // Comprueba si la respuesta HTTP fue valida con 200 y 299//
    throw new Error(                                 // La funcion genera un error que la interfaz captura y muestra al cliente  //
      `La API respondió con el estado HTTP ${response.status}.`
    );
  }

  return (await response.json()) as T;                 // Convierte el JSON del backend a un calor que JS pueda utilizar //
}

export function getObjects(): Promise<ObjectsResponse> {   // Obtenemos la lista de objetos
  return request<ObjectsResponse>("/api/v1/objects");
}

export function getObjectDetail(                        // Obtener detalles de un objeto
  objectId: string                                     // Recibe el identificador y consulta sus detalles
): Promise<AstronomicalObjectDetail> {
  return request<AstronomicalObjectDetail>(
    `/api/v1/objects/${encodeURIComponent(objectId)}`
  );
}
