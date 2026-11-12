"""Canalización completa de un candidato real, para CUALQUIER objeto.

Hace, en un solo paso, lo que antes estaba repartido en las prácticas 6, 7 y 9:

  1. Pregunta a SIMBAD las coordenadas, el movimiento propio y el paralaje del objeto.
  2. Calcula dónde está el objeto a mitad de la misión (ahí se centran todos los recortes,
     para que el movimiento se vea DENTRO del cuadro y no se cancele).
  3. Le pregunta a IRSA en qué fechas SPHEREx fotografió ese punto.
  4. Elige N épocas repartidas lo más lejos posible en el tiempo.
  5. Baja el recorte de cada época (no el archivo completo) y lo convierte a PNG, usando el
     MISMO contraste en todas: así, si el objeto cambia de brillo, el cambio se nota.
  6. Calcula la posición real del objeto en cada fecha, con su movimiento propio.
  7. Escribe el manifiesto y el bloque JSON listo para el visor. Con --publicar, además copia
     las imágenes al frontend y mete al objeto en src/mocks/objects.json.

Uso:
    python 10_candidatos.py --listar
    python 10_candidatos.py --target barnard
    python 10_candidatos.py --target wise0855 --epochs 5 --publicar
    python 10_candidatos.py --target "R Dra" --epochs 4     (cualquier nombre de SIMBAD)
"""

import argparse
import json
import shutil
import time
from pathlib import Path

import astropy.units as u
import numpy as np
import requests
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.visualization import AsinhStretch, PercentileInterval
from astropy.wcs import WCS
from PIL import Image

from targets import TARGETS, Target

SCIENCE_DIR = Path(__file__).resolve().parent
REPO_DIR = SCIENCE_DIR.parent.parent
FRONT_DIR = REPO_DIR / "labs" / "frontend" / "aladin-test"

IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP"
IRSA_BASE = "https://irsa.ipac.caltech.edu/"

# Fecha de referencia: a mitad del periodo que cubre SPHEREx hasta ahora. Los recortes se
# centran en la posición del objeto en esta fecha.
REFERENCE_DATE = "2026-03-01"

PNG_SIZE_PX = 512  # a cuánto se amplía el PNG (con suavizado); no agrega detalle real
MAX_RESULTS = 500


# ---------------------------------------------------------------- SIMBAD

def column(table, *names):
    """Busca una columna por nombre, sin importar mayúsculas (cambian entre versiones)."""
    lower = {c.lower(): c for c in table.colnames}
    for name in names:
        if name.lower() in lower:
            return table[lower[name.lower()]][0]
    return None


# Espejos de SIMBAD: si uno no responde (pasa seguido), se prueba el siguiente.
SIMBAD_SERVERS = ("simbad.cds.unistra.fr", "simbad.u-strasbg.fr", "simbad.harvard.edu")


def try_simbad(target: Target) -> dict | None:
    """Intenta SIMBAD en varios espejos. Devuelve posición y movimiento propio, o None."""
    from astroquery.simbad import Simbad

    for server in SIMBAD_SERVERS:
        service = Simbad()
        try:
            service.server = server
        except Exception:
            pass  # versiones viejas no dejan cambiar de espejo
        for campo in ("pmra", "pmdec", "plx_value"):
            try:
                service.add_votable_fields(campo)
            except Exception:
                pass  # el nombre del campo cambia entre versiones

        for alias in target.alias:
            try:
                table = service.query_object(alias)
            except Exception as error:
                print(f"  SIMBAD ({server}) falló con '{alias}': {str(error).splitlines()[0]}")
                break  # si el servidor no responde, no tiene caso probar más alias ahí
            if table is None or len(table) == 0:
                continue

            ra, dec = column(table, "ra"), column(table, "dec")
            if ra is None or dec is None:
                continue

            print(f"  SIMBAD ({server}) resolvió '{alias}' como: {column(table, 'main_id', 'MAIN_ID')}")
            return {
                "origen": f"SIMBAD ({server})",
                "ra": float(ra),
                "dec": float(dec),
                "pmra": column(table, "pmra", "PMRA"),
                "pmdec": column(table, "pmdec", "PMDEC"),
                "plx": column(table, "plx_value", "PLX_VALUE", "plx"),
            }
    return None


def try_sesame(target: Target) -> dict | None:
    """Segundo camino: el resolvedor de nombres Sesame del CDS. Solo da la posición."""
    for alias in target.alias:
        try:
            coord = SkyCoord.from_name(alias)
        except Exception as error:
            print(f"  Sesame falló con '{alias}': {str(error).splitlines()[0]}")
            continue
        print(f"  Sesame resolvió '{alias}' (solo posición, sin movimiento propio)")
        return {
            "origen": f"Sesame ({alias})",
            "ra": float(coord.ra.deg),
            "dec": float(coord.dec.deg),
            "pmra": None,
            "pmdec": None,
            "plx": None,
        }
    return None


def resolve_target(target: Target, cache_path: Path, usar_cache: bool, sin_red: bool) -> SkyCoord:
    """Posición y movimiento propio del objeto.

    Orden: caché en disco -> SIMBAD -> Sesame -> valores de respaldo de targets.py.
    Lo que se consigue se guarda en caché para no volver a consultar la red.
    """
    datos = None

    if usar_cache and cache_path.exists():
        datos = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"  Tomado del caché local ({datos.get('origen', 'desconocido')})")
    elif sin_red:
        raise SystemExit(
            f"No hay caché para '{target.name}' y se pidió --sin-red. Corre una vez con red."
        )
    else:
        datos = try_simbad(target) or try_sesame(target)

    if datos is None:
        if not target.respaldo.get("ra"):
            raise SystemExit(
                f"No se pudo resolver '{target.name}' y targets.py no tiene coordenadas de "
                "respaldo. Agrega ra y dec en el campo 'respaldo' y vuelve a intentar."
            )
        print("  Nadie respondió; se usan los valores de respaldo de targets.py.")
        datos = dict(target.respaldo)
        datos["origen"] = "respaldo (targets.py)"

    # Lo que falte se completa con el respaldo del catálogo.
    for clave in ("pmra", "pmdec", "plx"):
        valor = datos.get(clave)
        if valor is None or (isinstance(valor, float) and not np.isfinite(valor)):
            datos[clave] = target.respaldo.get(clave)

    pmra, pmdec = datos.get("pmra"), datos.get("pmdec")
    if pmra is None or pmdec is None:
        print(
            "  AVISO: no hay movimiento propio para este objeto. Se usa cero: las posiciones\n"
            "  serán las mismas en todas las épocas. Está bien para estrellas variables (que\n"
            "  cambian de brillo, no de lugar), pero NO para un objeto que se desplaza."
        )
        pmra, pmdec = 0.0, 0.0
        datos["pmra"], datos["pmdec"] = 0.0, 0.0

    plx = datos.get("plx") or 1.0  # si no hay paralaje, la distancia da igual aquí:
    # solo se aplica movimiento propio, no corrección por paralaje.
    datos["plx"] = plx

    print(
        f"  RA={datos['ra']:.6f}°, Dec={datos['dec']:.6f}°, "
        f"pmRA={float(pmra):.1f} mas/año, pmDec={float(pmdec):.1f} mas/año, "
        f"paralaje={float(plx):.2f} mas"
    )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    return SkyCoord(
        ra=float(datos["ra"]) * u.deg,
        dec=float(datos["dec"]) * u.deg,
        pm_ra_cosdec=float(pmra) * u.mas / u.yr,
        pm_dec=float(pmdec) * u.mas / u.yr,
        distance=(1000.0 / float(plx)) * u.pc,
        obstime=Time("J2000"),
        frame="icrs",
    )


def position_at(coord: SkyCoord, when: str) -> tuple[float, float]:
    """Posición (grados) del objeto en la fecha dada, por su movimiento propio."""
    moved = coord.apply_space_motion(new_obstime=Time(when, scale="utc"))
    return float(moved.ra.deg), float(moved.dec.deg)


# ---------------------------------------------------------------- IRSA

def query_observations(ra: float, dec: float, detector: str) -> list[dict]:
    """Observaciones de SPHEREx que cubren ese punto, ordenadas por fecha."""
    import pyvo

    query = f"""
    SELECT TOP {MAX_RESULTS}
        a.uri AS artifact_uri,
        p.time_bounds_lower AS observation_mjd,
        p.energy_bandpassname AS bandpass
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
    AND p.energy_bandpassname = 'SPHEREx-{detector}'
    ORDER BY p.time_bounds_lower
    """

    table = pyvo.dal.TAPService(IRSA_TAP).search(query).to_table()
    filas = []
    for row in table:
        mjd = float(row["observation_mjd"])
        filas.append(
            {
                "mjd": mjd,
                "utc": Time(mjd, format="mjd", scale="utc").isot,
                "uri": str(row["artifact_uri"]),
            }
        )
    filas.sort(key=lambda r: r["mjd"])
    return filas


def pick_spread(observations: list[dict], n: int) -> list[dict]:
    """Elige n observaciones repartidas lo más lejos posible unas de otras en el tiempo."""
    n = max(1, min(n, len(observations)))
    if n == 1:
        return [observations[len(observations) // 2]]

    mjds = [row["mjd"] for row in observations]
    chosen = {0, len(observations) - 1}
    while len(chosen) < n:
        best_i, best_gap = None, -1.0
        for i in range(len(observations)):
            if i in chosen:
                continue
            gap = min(abs(mjds[i] - mjds[c]) for c in chosen)
            if gap > best_gap:
                best_gap, best_i = gap, i
        chosen.add(best_i)
    return [observations[i] for i in sorted(chosen)]


def download_cutout(uri: str, ra: float, dec: float, size_deg: float, dest: Path, attempts: int = 8) -> None:
    """Baja el recorte centrado en (ra, dec). IRSA a veces responde 503; se reintenta."""
    url = f"{IRSA_BASE}{uri}?center={ra},{dec}d&size={size_deg}"
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=(15, 120))
            response.raise_for_status()
            dest.write_bytes(response.content)
            return
        except requests.exceptions.HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            if status in (503, 429) and attempt < attempts:
                wait = min(10 * attempt, 60)
                print(f"    IRSA respondió {status} (ocupado); reintento {attempt}/{attempts} en {wait}s...")
                time.sleep(wait)
                continue
            raise


# ---------------------------------------------------------------- imágenes

def read_image(fits_path: Path):
    """Lee la extensión IMAGE y devuelve (imagen, ra_centro, dec_centro, fov_grados, wcs)."""
    with fits.open(fits_path) as hdul:
        hdu = hdul["IMAGE"]
        image = np.asarray(hdu.data, dtype=float)
        wcs = WCS(hdu.header)
        ny, nx = image.shape
        ra_c, dec_c = wcs.all_pix2world(nx / 2, ny / 2, 0)
        fov = abs(wcs.pixel_scale_matrix[0, 0]) * max(nx, ny)
        return image, float(ra_c), float(dec_c), float(fov), wcs


def robust_sigma(values: np.ndarray) -> float:
    """Ruido típico, poco afectado por estrellas brillantes (MAD escalado)."""
    v = values[np.isfinite(values)]
    return float(1.4826 * np.median(np.abs(v - np.median(v))))


def clean_image(image: np.ndarray) -> tuple[np.ndarray, float]:
    """Resta el fondo (mediana) y marca como inválidos los píxeles anómalos muy negativos.

    En 4.4 a 5 micras el fondo térmico/zodiacal es enorme y cambia de una toma a otra, así
    que sin restarlo el contraste se gasta en el fondo y lo débil se pierde. Los píxeles por
    debajo de -5 sigma no son señal real (el ruido casi nunca llega ahí): son píxeles malos,
    y se pintan en gris neutro en vez de negro.
    """
    img = image - np.nanmedian(image)
    sigma = robust_sigma(img)
    img = np.where(img < -5 * sigma, np.nan, img)
    return img, sigma


def common_limits(images: list[np.ndarray], sigmas: list[float]) -> tuple[float, float]:
    """Mismos límites de contraste para todas las épocas (ya sin fondo).

    Es importante: si cada imagen se ajustara por separado, un objeto que cambia de brillo
    (como una estrella variable) se vería igual en todas y el cambio se perdería.
    Abajo: -2 sigma. Arriba: el percentil 99.5, pero nunca menos de 6 sigma (así, en un
    campo sin fuentes brillantes, el ruido no se amplifica hasta parecer señal).
    """
    sigma = float(np.median(sigmas))
    juntas = np.concatenate([img[np.isfinite(img)].ravel() for img in images])
    alto = PercentileInterval(99.5).get_limits(juntas)[1]
    return -2 * sigma, max(float(alto), 6 * sigma)


def save_png(image: np.ndarray, vmin: float, vmax: float, png_path: Path) -> None:
    stretch = AsinhStretch(a=0.1)
    finite = np.isfinite(image)
    norm = np.zeros_like(image)
    norm[finite] = stretch(np.clip((image[finite] - vmin) / (vmax - vmin), 0, 1))
    # Píxeles inválidos: gris del nivel de fondo (cero), no negro.
    nivel_fondo = np.array([np.clip((0 - vmin) / (vmax - vmin), 0, 1)], dtype=float)
    norm[~finite] = stretch(nivel_fondo)[0]
    pixels = (np.clip(norm, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(pixels, mode="L").resize((PNG_SIZE_PX, PNG_SIZE_PX), Image.BICUBIC).save(png_path)


def stack_aligned(items: list) -> np.ndarray | None:
    """Apila las épocas alineadas sobre la posición CALCULADA del objeto en cada fecha.

    items: lista de (imagen_sin_fondo, wcs, ra_objeto, dec_objeto). Cada imagen se desplaza
    (interpolación lineal) para que el objeto quede en el centro, y se promedian. Si el
    objeto emite algo, su señal se suma y el ruido baja cerca de raíz(N) veces. Las estrellas
    de fondo, que no se mueven, se emborronan: es lo esperado.
    """
    try:
        from scipy.ndimage import shift
    except ImportError:
        print("  (scipy no está instalado: se omite la imagen apilada)")
        return None

    sumas, pesos = [], []
    for img, wcs, ra, dec in items:
        ny, nx = img.shape
        x, y = wcs.all_world2pix(ra, dec, 0)
        delta = ((ny - 1) / 2 - float(y), (nx - 1) / 2 - float(x))
        valido = np.isfinite(img)
        sumas.append(shift(np.where(valido, img, 0.0), delta, order=1, mode="constant", cval=0.0))
        pesos.append(shift(valido.astype(float), delta, order=1, mode="constant", cval=0.0))

    h = min(a.shape[0] for a in sumas)
    w = min(a.shape[1] for a in sumas)

    def recorte(a: np.ndarray) -> np.ndarray:
        y0, x0 = (a.shape[0] - h) // 2, (a.shape[1] - w) // 2
        return a[y0 : y0 + h, x0 : x0 + w]

    total = sum(recorte(a) for a in sumas)
    peso = sum(recorte(a) for a in pesos)
    return np.where(peso > 0.5, total / np.maximum(peso, 1e-9), np.nan)


def report_stack(stack: np.ndarray) -> None:
    """Dice qué tan destacada es la posición del objeto (centro) frente al resto del ruido."""
    try:
        from scipy.ndimage import uniform_filter
    except ImportError:
        return
    filled = np.where(np.isfinite(stack), stack, 0.0)
    suave = uniform_filter(filled, size=3)  # media de 3x3 píxeles (aprox. el tamaño de la PSF)
    sigma = robust_sigma(suave)
    if sigma <= 0:
        return
    z = (suave - np.median(suave)) / sigma
    cy, cx = (stack.shape[0] - 1) // 2, (stack.shape[1] - 1) // 2
    centro = float(z[cy - 1 : cy + 2, cx - 1 : cx + 2].max())
    mejor = float(z.max())
    print(f"  En la posición del objeto (centro): {centro:.1f} sigma sobre el ruido")
    print(f"  Lo más brillante de toda la imagen apilada: {mejor:.1f} sigma")
    if centro >= 5:
        print("  -> Hay señal clara en la posición esperada.")
    elif centro >= 3:
        print("  -> Hay un indicio débil en la posición esperada (no concluyente).")
    else:
        print("  -> No se distingue del ruido en la posición esperada.")


# ---------------------------------------------------------------- publicar

def publish(target: Target, candidate: dict, output_dir: Path) -> None:
    """Copia las imágenes al frontend y mete (o actualiza) el objeto en objects.json."""
    public_dir = FRONT_DIR / "public" / "candidates" / target.key
    public_dir.mkdir(parents=True, exist_ok=True)
    for png in sorted(output_dir.glob("e*.png")):
        shutil.copy2(png, public_dir / png.name)
    print(f"  Imágenes copiadas a: {public_dir}")

    objects_path = FRONT_DIR / "src" / "mocks" / "objects.json"
    if not objects_path.exists():
        print(f"  Aviso: no encontré {objects_path}; no se actualizó objects.json.")
        return

    backup = objects_path.with_suffix(".json.bak")
    shutil.copy2(objects_path, backup)

    data = json.loads(objects_path.read_text(encoding="utf-8"))
    otros = [o for o in data.get("objects", []) if o.get("id") != candidate["id"]]
    data["objects"] = [candidate] + otros
    objects_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  objects.json actualizado (copia de seguridad en {backup.name})")


# ---------------------------------------------------------------- principal

def main() -> None:
    parser = argparse.ArgumentParser(description="Canalización de un candidato real de SPHEREx")
    parser.add_argument("--target", help="clave del catálogo (ver --listar) o nombre de SIMBAD")
    parser.add_argument("--epochs", type=int, default=5, help="cuántas épocas (por defecto 5)")
    parser.add_argument("--detector", default=None, help="detector de SPHEREx: D1 a D6")
    parser.add_argument("--size", type=float, default=None, help="ancho del recorte en grados")
    parser.add_argument("--publicar", action="store_true", help="copiar al frontend y actualizar objects.json")
    parser.add_argument("--listar", action="store_true", help="muestra el catálogo y termina")
    parser.add_argument("--refrescar", action="store_true", help="ignora el caché y vuelve a consultar")
    parser.add_argument(
        "--sin-red",
        action="store_true",
        help="usa solo lo que ya está guardado en disco; no consulta SIMBAD ni IRSA",
    )
    args = parser.parse_args()

    if args.listar or not args.target:
        print("Objetos en el catálogo (targets.py):\n")
        for key, t in TARGETS.items():
            print(f"  {key:12} {t.name}  ({t.kind}, detector {t.detector})")
        print("\nTambién puedes pasar cualquier nombre que SIMBAD reconozca con --target.")
        return

    # El objetivo puede venir del catálogo o ser un nombre suelto de SIMBAD.
    if args.target in TARGETS:
        target = TARGETS[args.target]
    else:
        clave = args.target.lower().replace(" ", "-").replace("*", "").strip("-")
        target = Target(
            key=clave,
            alias=(args.target,),
            name=args.target,
            kind="unknown",
            summary=f"Objeto consultado a SIMBAD: {args.target}. Imágenes reales de SPHEREx (IRSA).",
        )
        print(f"'{args.target}' no está en el catálogo: se consulta directo a SIMBAD.")

    detector = args.detector or target.detector
    size_deg = args.size or target.cutout_deg

    output_dir = SCIENCE_DIR / "outputs" / "candidatos" / target.key
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    usar_cache = not args.refrescar

    print(f"\n=== {target.name} ({target.key}) ===")
    print("1. Posición y movimiento propio del objeto...")
    coord = resolve_target(target, cache_dir / "objeto.json", usar_cache, args.sin_red)

    print(f"\n2. Posición a la fecha de referencia ({REFERENCE_DATE}):")
    ra_ref, dec_ref = position_at(coord, REFERENCE_DATE)
    print(f"  RA={ra_ref:.6f}°, Dec={dec_ref:.6f}° (aquí se centran todos los recortes)")

    print(f"\n3. Observaciones de SPHEREx (detector {detector})...")
    obs_cache = cache_dir / f"observaciones_{detector}.json"
    if usar_cache and obs_cache.exists():
        observations = json.loads(obs_cache.read_text(encoding="utf-8"))
        print(f"  Tomadas del caché local: {obs_cache.name}")
    elif args.sin_red:
        raise SystemExit("No hay caché de observaciones y se pidió --sin-red.")
    else:
        print("  Consultando IRSA...")
        observations = query_observations(ra_ref, dec_ref, detector)
        obs_cache.write_text(json.dumps(observations, indent=2), encoding="utf-8")
    print(f"  Observaciones encontradas: {len(observations)}")
    if not observations:
        raise SystemExit(
            "SPHEREx no ha cubierto esa posición en este detector. Prueba otro con --detector."
        )

    chosen = pick_spread(observations, args.epochs)
    span = chosen[-1]["mjd"] - chosen[0]["mjd"]
    print(f"  Épocas elegidas: {len(chosen)} (abarcan {span:.1f} días)")

    print(f"\n4. Recortes de {size_deg}°...")
    descargadas = []
    for i, row in enumerate(chosen, start=1):
        fits_path = output_dir / f"e{i}.fits"
        if not fits_path.exists():
            if args.sin_red:
                print(f"  Época {i}: no está descargada y se pidió --sin-red; se omite.")
                continue
            print(f"  Época {i} ({row['utc'][:19]}): descargando...")
            try:
                download_cutout(row["uri"], ra_ref, dec_ref, size_deg, fits_path)
            except Exception as error:
                print(f"    No se pudo descargar, se omite: {error}")
                continue
        else:
            print(f"  Época {i} ({row['utc'][:19]}): ya estaba descargada.")
        descargadas.append((i, row, fits_path))

    if not descargadas:
        raise SystemExit("No se pudo descargar ninguna época. Intenta más tarde.")

    print("\n5. Restando el fondo y convirtiendo a PNG (mismo contraste en todas las épocas)...")
    leidas = [read_image(fits_path) for _, _, fits_path in descargadas]
    limpias, sigmas = [], []
    for image, *_ in leidas:
        limpia, sigma = clean_image(image)
        limpias.append(limpia)
        sigmas.append(sigma)
    vmin, vmax = common_limits(limpias, sigmas)

    positions = []
    manifest = []
    alineables = []
    for (i, row, fits_path), (image, ra_c, dec_c, fov, wcs), limpia in zip(descargadas, leidas, limpias):
        png_path = output_dir / f"e{i}.png"
        save_png(limpia, vmin, vmax, png_path)
        ra_real, dec_real = position_at(coord, row["utc"])
        alineables.append((limpia, wcs, ra_real, dec_real))
        print(
            f"  e{i}: {row['utc'][:10]} | centro RA={ra_c:.5f}, Dec={dec_c:.5f}, FOV={fov:.4f}° "
            f"| objeto RA={ra_real:.5f}, Dec={dec_real:.5f}"
        )
        manifest.append(
            {
                "epochId": f"e{i}",
                "observedAtUtc": row["utc"],
                "imageCenterRa": ra_c,
                "imageCenterDec": dec_c,
                "fovDeg": fov,
                "objectRa": ra_real,
                "objectDec": dec_real,
                "imageFile": png_path.name,
            }
        )
        positions.append(
            {
                "epochId": f"e{i}",
                "observedAt": row["utc"][:10],
                "ra": round(ra_real, 6),
                "dec": round(dec_real, 6),
                "imageUrl": f"/candidates/{target.key}/e{i}.png",
                "fovDeg": round(fov, 5),
            }
        )

    if len(alineables) >= 2:
        print("\n   Imagen apilada (épocas alineadas sobre la posición calculada del objeto):")
        apilada = stack_aligned(alineables)
        if apilada is not None:
            sigma_ap = robust_sigma(apilada)
            alto = PercentileInterval(99.5).get_limits(apilada[np.isfinite(apilada)])[1]
            save_png(apilada, -2 * sigma_ap, max(float(alto), 6 * sigma_ap), output_dir / "apilada.png")
            print(f"  Guardada: {output_dir / 'apilada.png'}")
            report_stack(apilada)

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    candidate = {
        "id": target.key,
        "kind": target.kind,
        "name": target.name,
        "summary": target.summary,
        "positions": positions,
    }
    (output_dir / "candidate.json").write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\n6. Resultados en: {output_dir}")
    print("  manifest.json (detalle) y candidate.json (bloque listo para el visor)")

    if args.publicar:
        print("\n7. Publicando en el frontend...")
        publish(target, candidate, output_dir)
    else:
        print("\n  (Usa --publicar para copiar las imágenes al visor y actualizar objects.json)")


if __name__ == "__main__":
    main()
