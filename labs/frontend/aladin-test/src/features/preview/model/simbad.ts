/**
 * Consultas a SIMBAD desde el navegador, por TAP (ADQL).
 *
 * Por qué no usamos la capa ni el puntero de Aladin: consultan a alasky/CDS, que desde algunas
 * redes responde 404 o bloquea por CORS. Aquí se consulta directo al servicio TAP: primero el
 * espejo de Harvard (que sí permite peticiones desde el navegador) y, si falla, el de CDS.
 */

const MIRRORS = ["simbad.harvard.edu", "simbad.cds.unistra.fr"];
const TIMEOUT_MS = 12000;

/** Con un campo más ancho que esto no se consulta: el cielo se llenaría de marcas. */
export const MAX_FOV_FOR_LAYER = 6;

/** Máximo de objetos que se dibujan (los más citados). */
const FIELD_LIMIT = 150;
/**
 * Cuántos se piden a SIMBAD. Se piden sin ordenar y se ordenan aquí: con `ORDER BY nbref` el servidor
 * tardaba ~16 s en una consulta que sin ordenar tarda ~0.1 s.
 */
const FETCH_LIMIT = 500;

export type SimbadObject = {
  /** Número interno de SIMBAD: sin ambigüedad, a diferencia del nombre (que puede traer apóstrofes o espacios dobles). */
  oid: number;
  /** Identificador principal de SIMBAD, p. ej. "V* R Dra". */
  id: string;
  /** Código de tipo de SIMBAD, p. ej. "Mi*". */
  otype: string;
  ra: number;
  dec: number;
  /** Cuántos artículos citan al objeto: sirve para mostrar primero los más conocidos. */
  nbref: number;
};

export type SimbadDetails = {
  id: string;
  otype: string;
  /** Nombre del tipo en español si lo conocemos; si no, el de SIMBAD (en inglés). */
  typeLabel: string;
  ra: number;
  dec: number;
  spectralType?: string;
  parallaxMas?: number;
  pmRaMasYr?: number;
  pmDecMasYr?: number;
  radialVelocityKmS?: number;
  magnitudes: Partial<Record<"B" | "V" | "G" | "J" | "H" | "K", number>>;
  nbref: number;
};

/* ------------------------------ utilidades ------------------------------ */

const num = (v: unknown): number | undefined => (typeof v === "number" && Number.isFinite(v) ? v : undefined);
const str = (v: unknown): string | undefined => (typeof v === "string" && v.trim() !== "" ? v.trim() : undefined);


/**
 * Ejecuta una consulta ADQL y devuelve filas como objetos { columna: valor }.
 * Prueba cada espejo con tiempo límite; si la persona cancela (signal), se corta sin probar otro.
 */
async function runAdql(adql: string, signal?: AbortSignal): Promise<Record<string, unknown>[]> {
  let lastError: unknown = new Error("No se pudo consultar SIMBAD.");

  for (const host of MIRRORS) {
    const local = new AbortController();
    const timer = setTimeout(() => local.abort(), TIMEOUT_MS);
    const forward = () => local.abort();
    signal?.addEventListener("abort", forward);

    try {
      const url = `https://${host}/simbad/sim-tap/sync?request=doQuery&lang=adql&format=json&query=${encodeURIComponent(adql)}`;
      const res = await fetch(url, { signal: local.signal });
      if (!res.ok) throw new Error(`SIMBAD respondió HTTP ${res.status}.`);
      const json = (await res.json()) as { metadata: { name: string }[]; data: unknown[][] };
      const names = json.metadata.map((m) => m.name);
      return json.data.map((row) => Object.fromEntries(row.map((value, i) => [names[i], value])));
        } catch (error) {
      if (signal?.aborted) throw error; // la cancelación es voluntaria: no es un fallo del servidor
      lastError = error;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", forward);
    }
  }
  throw lastError;
}

/* ------------------------------ tipos en español ------------------------------ */

// Solo los códigos que conocemos con certeza; el resto usa el nombre largo de SIMBAD.
const TYPE_ES: Record<string, string> = {
  "*": "Estrella",
  "**": "Estrella doble o múltiple",
  "V*": "Estrella variable",
  "Mi*": "Variable tipo Mira",
  "BD*": "Enana marrón",
  "Y*O": "Objeto estelar joven",
  "Em*": "Estrella de líneas de emisión",
  HII: "Región H II",
  PN: "Nebulosa planetaria",
  SNR: "Remanente de supernova",
  G: "Galaxia",
  GlC: "Cúmulo globular",
  OpC: "Cúmulo abierto",
  "Cl*": "Cúmulo de estrellas",
  "As*": "Asociación de estrellas",
  QSO: "Cuásar",
  AGN: "Núcleo galáctico activo",
};

/**
 * Umbrales de citas, del más permisivo al más estricto. Pedir "500 cualesquiera" a SIMBAD devuelve una
 * muestra amontonada en un rincón del campo (medido: RA 274–277 de un campo de 270–277); filtrar por
 * citas reparte los objetos por todo el campo y evita el ORDER BY, que tardaba ~16 s.
 */
const NBREF_STEPS = [0, 5, 20, 100, 500];

/** Por dónde empezar según el radio: en campos anchos un umbral bajo se llenaría casi seguro. */
function firstStep(radiusDeg: number) {
  if (radiusDeg > 2) return 2; // nbref >= 20
  if (radiusDeg > 0.7) return 1; // nbref >= 5
  return 0; // sin filtro
}
/* ------------------------------ consultas ------------------------------ */

/** Objetos conocidos dentro de un círculo del cielo, los más citados primero. */
export async function findObjectsInField(
  raDeg: number,
  decDeg: number,
  radiusDeg: number,
  signal?: AbortSignal,
): Promise<SimbadObject[]> {
  const cone = `CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', ${raDeg}, ${decDeg}, ${radiusDeg}))=1`;

  // Si la respuesta llena el tope, es solo una parte del campo: se repite con un umbral más estricto.
  let rows: Record<string, unknown>[] = [];
  for (let step = firstStep(radiusDeg); step < NBREF_STEPS.length; step++) {
    const min = NBREF_STEPS[step];
    const adql =
      `SELECT TOP ${FETCH_LIMIT} main_id, oid, otype, ra, dec, nbref FROM basic ` +
      `WHERE ${cone}${min > 0 ? ` AND nbref >= ${min}` : ""}`;
    rows = await runAdql(adql, signal);
    if (rows.length < FETCH_LIMIT) break;
  }

  const objects: SimbadObject[] = [];
  for (const r of rows) {
    const id = str(r.main_id);
    const oid = num(r.oid);
    const ra = num(r.ra);
    const dec = num(r.dec);
    if (id && oid !== undefined && ra !== undefined && dec !== undefined) {
      objects.push({ oid, id, otype: str(r.otype) ?? "?", ra, dec, nbref: num(r.nbref) ?? 0 });
    }
  }
  objects.sort((a, b) => b.nbref - a.nbref);
  return objects.slice(0, FIELD_LIMIT);
}

/** Ficha completa de un objeto, para la tarjeta que se abre al hacer clic. */
export async function getObjectDetails(oid: number, signal?: AbortSignal): Promise<SimbadDetails | null> {
  const adql =
    `SELECT basic.main_id, basic.otype, basic.ra, basic.dec, basic.sp_type, basic.plx_value, ` +
    `basic.pmra, basic.pmdec, basic.rvz_radvel, basic.nbref, otypedef.otype_longname, ` +
    `allfluxes.B, allfluxes.V, allfluxes.G, allfluxes.J, allfluxes.H, allfluxes.K ` +
    `FROM basic LEFT JOIN otypedef ON basic.otype = otypedef.otype ` +
    `LEFT JOIN allfluxes ON basic.oid = allfluxes.oidref ` +
    `WHERE basic.oid = ${Math.trunc(oid)}`;

  const [r] = await runAdql(adql, signal);
  if (!r) return null;

  const ra = num(r.ra);
  const dec = num(r.dec);
  if (ra === undefined || dec === undefined) return null;

  const otype = str(r.otype) ?? "?";
  const magnitudes: SimbadDetails["magnitudes"] = {};
  for (const band of ["B", "V", "G", "J", "H", "K"] as const) {
    const m = num(r[band]);
    if (m !== undefined) magnitudes[band] = m;
  }

  return {
    id: str(r.main_id) ?? String(oid),
    otype,
    typeLabel: TYPE_ES[otype] ?? str(r.otype_longname) ?? otype,
    ra,
    dec,
    spectralType: str(r.sp_type),
    parallaxMas: num(r.plx_value),
    pmRaMasYr: num(r.pmra),
    pmDecMasYr: num(r.pmdec),
    radialVelocityKmS: num(r.rvz_radvel),
    magnitudes,
    nbref: num(r.nbref) ?? 0,
  };
}