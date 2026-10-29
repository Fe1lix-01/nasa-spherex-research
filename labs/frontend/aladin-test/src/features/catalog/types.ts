export type AstronomicalObservation = {                  // Contrato de los datos //
  id: string;                           // Representa la observacion astronomica individual y como se representa desde el backend //
  detector: string;
  filename: string;
  format: string;
};

export type AstronomicalObjectSummary = {        // Representa el resumen de un objeto astronomico en el catalogo //
  id: string;
  name: string;
  observation_count: number;
  detectors: string[];
};

export type AstronomicalObjectDetail =          // Representa el detalle completo de un objeto //
  AstronomicalObjectSummary & {                // Contiene todas la propiedadeds del resumen mas una propiedad adicional //
    observations: AstronomicalObservation[];
  };

export type ObjectsResponse = {            // Respuesta completa del endpoint //
  total: number;
  objects: AstronomicalObjectSummary[];
};
