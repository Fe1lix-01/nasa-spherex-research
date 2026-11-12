/**
 * Contrato de datos entre el frontend y el back (BORRADOR, pendiente de acordar con el back).
 *
 * Unidades: coordenadas en grados (sistema ICRS), longitudes de onda en micrómetros (µm),
 * fechas en ISO 8601 y márgenes de error en segundos de arco.
 */

/** Una de las observaciones de SPHEREx (el satélite cubre todo el cielo cada ~6 meses). */
export type Epoch = {
  id: string; // "e1", "e2", "e3"
  observedAt: string; // fecha ISO 8601, p. ej. "2025-06-01"
  label: string; // texto para mostrar a las personas: "Época 1"
};

/** Una de las 102 bandas de luz infrarroja. Solo metadatos: las imágenes se piden aparte. */
export type Band = {
  index: number; // 1 a 102
  wavelengthMinUm: number; // inicio del rango, en µm
  wavelengthMaxUm: number; // fin del rango, en µm
};

/** Posición de un objeto en el cielo, medida en una época. */
export type SkyPosition = {
  epochId: string; // en qué época se midió
  ra: number; // ascensión recta, en grados
  dec: number; // declinación, en grados
  /**
   * Los tres campos siguientes solo los traen los candidatos con datos REALES (los que se
   * bajaron de IRSA con su propio recorte por época). Los objetos simulados no los traen y
   * comparten las imágenes del recuadro de prueba.
   */
  observedAt?: string; // fecha real de esta observación (ISO 8601)
  imageUrl?: string; // imagen de esta época, p. ej. "/candidates/barnard/e1.png"
  fovDeg?: number; // ancho real del recorte, en grados
};

/** Tipos de objeto. Los valores van en inglés; la interfaz los traduce al español. */
export type ObjectKind = "asteroid" | "comet" | "star" | "brown_dwarf" | "planet_candidate" | "nebula" | "unknown";

/** Un objeto que cambia de posición entre épocas, con su predicción si se pudo calcular. */
export type MovingObject = {
  id: string;
  kind: ObjectKind;
  name?: string; // opcional: no todos tienen nombre conocido
  summary?: string; // explicación breve para mostrar a las personas (opcional)
  positions: SkyPosition[]; // una por cada época en la que se detectó
  /** Opcional: no siempre hay suficientes épocas para predecir. */
  prediction?: {
    atDate: string; // fecha futura de la predicción (ISO 8601)
    ra: number;
    dec: number;
    uncertaintyArcsec: number; // radio del círculo de incertidumbre, en segundos de arco
    confidence: number; // de 0 a 1
  };
};

/** Zona del cielo a la que corresponden los objetos. */
export type SkyRegion = {
  ra: number; // centro, en grados
  dec: number;
  fovDeg: number; // campo de visión, en grados
};

/** Respuesta con los objetos de una región. */
export type ObjectsResponse = {
  simulated?: boolean; // true cuando son datos de prueba
  region: SkyRegion;
  objects: MovingObject[];
};

/** Una imagen de una época, sobre la que se dibujan los objetos. */
export type Frame = {
  epochId: string; // "e1", "e2", "e3"
  imageUrl: string; // imagen ya convertida a PNG, p. ej. "/frames/epoca1_D6.png"
  ra: number; // centro de la imagen, en grados (ICRS)
  dec: number;
  fovDeg: number; // ancho de la imagen, en grados (la imagen es cuadrada)
};
