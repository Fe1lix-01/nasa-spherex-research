export type Phenomenon = {
  id: string;
  title: string;
  /** Frase corta que aparece bajo el título. */
  tagline: string;
  /** Miniatura en /public/fenomenos. Si no existe, se muestra la ilustración de respaldo. */
  image: string;
};

export const PHENOMENA: Phenomenon[] = [
  { id: "nebulosa", title: "Nebulosas", tagline: "Polvo que oculta, luz que revela.", image: "/fenomenos/nebulosas.jpg" },
  // ...las otras cinco igual: galaxias, protoestrellas, hielos, cometas, estructura
];