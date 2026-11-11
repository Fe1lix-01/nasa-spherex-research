import type { ObjectKind } from "@/contracts";

/** Nombres en español para los tipos de objeto. La interfaz siempre va en español. */
export const KIND_LABELS: Record<ObjectKind, string> = {
  asteroid: "Asteroide",
  comet: "Cometa",
  star: "Estrella",
  brown_dwarf: "Enana marrón",
  planet_candidate: "Candidato a planeta",
  unknown: "Objeto desconocido",
};
