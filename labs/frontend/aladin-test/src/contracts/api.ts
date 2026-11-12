/**
 * Contratos correspondientes a las respuestas reales de ETER API.
 *
 * Estos modelos representan los datos que entrega FastAPI.
 * Se mantienen separados de los contratos de demostración
 * utilizados por la vista previa del frontend.
 */

/** Detectores disponibles en las observaciones SPHEREx. */
export type Detector = "D1" | "D2" | "D3" | "D4" | "D5" | "D6";

/** Metadatos de un archivo FITS procesados por el backend. */
export interface FrameMetadata {
  id: string;
  detector: Detector;
  filename: string;
  format: "FITS";

  width: number;
  height: number;

  center_ra_deg: number;
  center_dec_deg: number;

  pixel_scale_x_arcsec: number;
  pixel_scale_y_arcsec: number;

  fov_x_deg: number;
  fov_y_deg: number;

  coordinate_system: string;
  projection: string;
}

/** Respuesta del endpoint GET /api/v1/frames. */
export interface FramesResponse {
  total: number;
  frames: FrameMetadata[];
}

/** Representa una observación individual de un objeto. */
export interface Observation {
  id: string;
  detector: Detector;
  filename: string;
  format: "FITS";
}

/** Información resumida de un objeto astronómico. */
export interface AstronomicalObjectSummary {
  id: string;
  name: string;
  observation_count: number;
  detectors: Detector[];
  local_observation_count: number;
  remote_observation_count: number;
}

/** Producto remoto encontrado mediante una consulta espacial a IRSA. */
export interface RemoteObservation {
  observation_id: string;
  product_id: string;
  collection: "spherex_qr2" | "spherex_qr3";
  band: string;
  start_mjd: number;
  end_mjd: number;
  start_utc: string;
  image_center_ra_deg: number;
  image_center_dec_deg: number;
  access_url: string;
  access_format: string;
}

/** Información completa de un objeto y sus observaciones. */
export interface AstronomicalObjectDetail extends AstronomicalObjectSummary {
  observations: Observation[];
  remote_observations: RemoteObservation[];
  remote_association?: {
    type: "spatial_intersection";
    description: string;
  } | null;
  remote_query?: {
    collection: "spherex_qr2" | "spherex_qr3";
    ra: number;
    dec: number;
    radius_arcsec: number;
    band: string;
    limit: number;
  } | null;
  science_preview?: {
    title: string;
    description: string;
  } | null;
}

/** Respuesta del endpoint GET /api/v1/objects. */
export interface ObjectsResponse {
  total: number;
  objects: AstronomicalObjectSummary[];
}

/** Respuesta del endpoint GET /api/v1/observations. */
export interface ObservationsResponse {
  total: number;
  observations: Observation[];
}