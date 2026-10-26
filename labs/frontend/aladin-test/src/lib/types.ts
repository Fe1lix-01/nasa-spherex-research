/** Valores r, g, b entre 0 y 1. */
export type RGB = [number, number, number];

export type FilterId = "visible" | "nir" | "mir" | "ice" | "thermal" | "comp";

/**
 * Cada "capa" guarda cuánta luz hay en una banda, por píxel (0 a 1 aprox.).
 * Con datos reales de SPHEREx, cada capa saldría de una banda distinta.
 */
export type Layers = {
  v: Float32Array; // luz visible (estrellas, galaxia, nebulosa)
  neb: Float32Array; // emisión de la nebulosa (tinte magenta)
  ir: Float32Array; // infrarrojo cercano
  th: Float32Array; // térmico (calor del polvo)
  ice: Float32Array; // absorción de hielos (~3 µm)
};

export type FilterDef = {
  id: FilterId;
  name: string;
  band: string;
  desc: string;
  /** null = sin filtro (vista visible). Escribe el color resultante en `out`. */
  fn:
    | ((
        v: number,
        neb: number,
        ir: number,
        th: number,
        ice: number,
        out: RGB
      ) => void)
    | null;
};
