"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import type { Epoch, Frame, MovingObject } from "@/contracts";
import ControlPanel from "@/features/viewer/components/ControlPanel";
import ViewerShell from "@/features/viewer/components/ViewerShell";
import MenuDrawer from "@/features/menu/MenuDrawer";
import { SvgDefs } from "@/features/phenomena/SvgDefs";
import { FILTERS } from "@/features/viewer/engine/filters";
import AladinBackground from "@/features/sky-viewer/AladinBackground";
import { ALLWISE_HIPS_URL } from "@/features/sky-viewer/aladinDocument";
import { skyData } from "@/services";
import MarkerLayer, { type Marker } from "./components/epochs/MarkerLayer";
import PreviewCard from "./components/panel/PreviewCard";
import { matchObject } from "@/features/preview/model/objectsMatch";
import { skyToImage } from "@/features/preview/model/projection";
import PanZoom from "./components/epochs/PanZoom";
import CollapsiblePanel from "./components/panel/CollapsiblePanel";
import TopRightTools from "./components/search/TopRightTools";
import PreviewCredit from "./components/panel/PreviewCredit";
import EpochLayer from "./components/epochs/EpochLayer";
import PlaybackBar from "./components/epochs/PlaybackBar";
import TrailLayer from "./components/epochs/TrailLayer";
import ModeToggle, { type ViewMode } from "./components/panel/ModeToggle";
import SkyStage from "./components/sky/SkyStage";
import { skyCssFilter } from "./components/sky/skyFilters";
import { useEpochClock } from "./hooks/useEpochClock";
import {
  epochsForObject,
  hasOwnImages,
  positionAt,
  trackPoints,
} from "@/features/preview/model/trajectory";

/** A dónde mira el mosaico. `nonce` cambia en cada búsqueda para volver a ir aunque sea al mismo punto. */
type SkyTarget = { raDeg: number; decDeg: number; fovDeg: number; nonce: number };
const ALL_SKY: SkyTarget = { raDeg: 0, decDeg: 0, fovDeg: 360, nonce: 0 };
const CLOSE_UP_FOV_DEG = 1.5; // campo al ir a un candidato o a unas coordenadas
const TEST_LABEL = "Prueba"; // nombre de la zona con imágenes simuladas

/** Campo de visión del recuadro de un candidato real, si su dato no lo trae. */
const REAL_PATCH_FOV_DEG = 0.08;
/**
 * Qué tanto se acerca el mosaico al elegir un candidato con imágenes reales. Los recortes de
 * SPHEREx son pequeños (unos minutos de arco), así que hay que acercarse mucho para que el
 * recuadro ocupe buena parte de la pantalla.
 */
const REAL_CLOSE_UP_FOV_DEG = 0.14;

/**
 * Opacidad de la capa de la época i en el instante t. La primera siempre está debajo y
 * opaca; cada una de las siguientes aparece de forma gradual cuando t llega a su época.
 */
const layerOpacity = (i: number, t: number) => (i === 0 ? 1 : Math.min(Math.max(t - (i - 1), 0), 1));

/**
 * Vista previa de movimiento dentro del visor de ÉTER. Tiene dos modos:
 *  - Mosaico del cielo: el mapa interactivo de Aladin (AllWISE como referencia). Encima se
 *    pinta el recuadro del candidato elegido: si es un candidato con datos REALES (sus
 *    propias imágenes por época, bajadas de IRSA), se usan esas; si es uno de los objetos
 *    simulados, se usan las imágenes de prueba compartidas.
 *  - Épocas simuladas: las imágenes de prueba solas, a pantalla completa.
 */
export default function PreviewPanel() {
  const [frames, setFrames] = useState<Frame[] | null>(null);
  const [objects, setObjects] = useState<MovingObject[]>([]);
  const [epochs, setEpochs] = useState<Epoch[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sceneError, setSceneError] = useState<string | null>(null);
  const [filterIndex, setFilterIndex] = useState(0);
  const [inten, setInten] = useState(72);
  const [gain, setGain] = useState(110);
  const [marker, setMarker] = useState<Marker | null>(null);
  const [outside, setOutside] = useState(false);
  const [selected, setSelected] = useState<MovingObject | null>(null);
  const [cardOpen, setCardOpen] = useState(true); // la tarjeta se puede cerrar sin deseleccionar el objeto
  const [epochsOpen, setEpochsOpen] = useState(true); // mostrar u ocultar selector de modo y reproducción
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [revision, setRevision] = useState(0);
  const [mode, setMode] = useState<ViewMode>("sky");
  const [skyTarget, setSkyTarget] = useState<SkyTarget>(ALL_SKY);
  const [skyOpened, setSkyOpened] = useState(true); // el mapa se crea la primera vez que se entra
  const [skyFailed, setSkyFailed] = useState(false); // si falla, se usa el visor básico de Felix

  useEffect(() => {
    Promise.all([skyData.getFrames(), skyData.getObjects(), skyData.getEpochs()])
      .then(([f, o, e]) => {
        setFrames(f);
        setObjects(o.objects);
        setEpochs(e);
      })
      .catch(() => setLoadError("No se pudieron cargar los datos de la vista previa."));
  }, []);

  const frame = frames?.[0] ?? null;
  const filter = FILTERS[filterIndex];
  const skyMode = mode === "sky";

  // ¿El candidato elegido trae sus propias imágenes por época? Entonces son datos reales y
  // manda su propia línea de tiempo (por ejemplo, Barnard con 5 épocas de IRSA).
  const realObject = selected && hasOwnImages(selected) ? selected : null;
  const track = selected ? trackPoints(selected) : [];

  // Cuántas épocas tiene la animación en curso: las del candidato real, o las compartidas.
  const epochCount = realObject ? realObject.positions.length : frames?.length ?? 0;
  const clock = useEpochClock(epochCount, 3);

  // Las fechas que muestran la barra de reproducción y el recuadro de información.
  const shownEpochs = epochsForObject(realObject, epochs);

  const changeMode = (next: ViewMode) => {
    if (next === "sky") setSkyOpened(true);
    setMode(next);
  };

  const goSky = (raDeg: number, decDeg: number, fovDeg: number) =>
    setSkyTarget((s) => ({ raDeg, decDeg, fovDeg, nonce: s.nonce + 1 }));

  const onSkyFail = (message: string) => {
    setSkyFailed(true);
    setSceneError(`${message} Se usa el visor básico de Aladin.`);
  };

  const search = (ra: number, dec: number) => {
    if (!frame) return;
    setOutside(skyToImage(ra, dec, frame) === null);
    setMarker({ id: `${ra},${dec}`, label: `${ra.toFixed(4)}, ${dec.toFixed(4)}`, ra, dec });
    goSky(ra, dec, CLOSE_UP_FOV_DEG);
    // Si las coordenadas caen cerca de un candidato (0.5°), abrimos su recuadro.
    setSelected(matchObject(ra, dec, objects, 0.5));
    setCardOpen(true);
  };

  const pickCandidate = (obj: MovingObject) => {
    const first = trackPoints(obj)[0];
    if (!first) return;
    const real = hasOwnImages(obj);
    setOutside(!real && frame ? skyToImage(first.ra, first.dec, frame) === null : false);
    setMarker(null); // el marcador del candidato lo dibuja la animación
    // Los recortes reales son pequeños (unos minutos de arco), así que hay que acercarse más.
    goSky(first.ra, first.dec, real ? REAL_CLOSE_UP_FOV_DEG : CLOSE_UP_FOV_DEG);
    setSelected(obj);
    setCardOpen(true);
    if (real) setMode("sky"); // las imágenes reales solo se ven sobre el mosaico
    clock.seek(0);
  };

  const message = loadError ?? (!frame ? "Cargando imágenes…" : null);

  // Lo que muestra el selector de arriba: el candidato elegido, o "custom" si buscaron coordenadas.
  const selectValue = selected?.id ?? (marker ? "custom" : "");

  // Marcadores: el de las coordenadas buscadas (fijo) y el del candidato (se mueve con t).
  const markers: Marker[] = [];
  if (marker) markers.push(marker);
  const moving = selected ? positionAt(selected, clock.t) : null;
  if (selected && moving) {
    markers.push({ id: `${selected.id}-now`, label: selected.name ?? selected.id, ...moving });
  }

  // "Reiniciar visor": vuelve al zoom inicial, detiene la animación y limpia marcador y recuadro.
  const resetViewer = () => {
    clock.pause();
    clock.seek(0);
    setRevision((n) => n + 1);
    setMarker(null);
    setSelected(null);
    setOutside(false);
    goSky(ALL_SKY.raDeg, ALL_SKY.decDeg, ALL_SKY.fovDeg);
  };

  // Capas de las imágenes de prueba compartidas (las 3 simuladas).
  const demoLayers = frames?.map((f, i) => (
    <EpochLayer
      key={f.epochId}
      imageUrl={f.imageUrl}
      filter={filter}
      inten={inten}
      gain={gain}
      opacity={layerOpacity(i, clock.t)}
      onError={setSceneError}
    />
  ));

  // Capas del recuadro sobre el mosaico: las del candidato real, si las tiene; si no, las de prueba.
  const patchLayers = realObject
    ? track.map((p, i) => (
        <EpochLayer
          key={`${realObject.id}-${p.index}`}
          imageUrl={p.imageUrl as string}
          filter={filter}
          inten={inten}
          gain={gain}
          opacity={layerOpacity(i, clock.t)}
          onError={setSceneError}
        />
      ))
    : demoLayers;

  // Dónde y de qué tamaño va el recuadro en el cielo.
  const patch =
    realObject && track[0]
      ? {
          ra: track[0].ra,
          dec: track[0].dec,
          fovDeg: track[0].fovDeg ?? REAL_PATCH_FOV_DEG,
          label: realObject.name ?? realObject.id,
        }
      : {
          ra: frame?.ra ?? 209.4201,
          dec: frame?.dec ?? 53.9431,
          fovDeg: frame?.fovDeg ?? 3.5,
          label: TEST_LABEL,
        };

  return (
    <ViewerShell
      background={
        <>
          {skyOpened && !skyFailed && (
            <SkyStage
              active={skyMode}
              target={skyTarget}
              cssFilter={skyCssFilter(filter.id, inten, gain)}
              patch={patch}
              patchContent={skyMode ? patchLayers : null}
              markers={markers}
              trail={track}
              t={clock.t}
              onFail={onSkyFail}
            />
          )}
          {skyMode && skyFailed && (
            <AladinBackground
              key={revision}
              position={{ raDeg: skyTarget.raDeg, decDeg: skyTarget.decDeg }}
              fovDeg={skyTarget.fovDeg}
              surveyUrl={ALLWISE_HIPS_URL}
              style={{ marginTop: 88, height: "calc(100% - 88px)" }}
              title="Mosaico del cielo infrarrojo AllWISE"
            />
          )}
          {!skyMode && (
            // A pantalla completa solo viven las imágenes simuladas: el rastro y el marcador
            // de un candidato real se dibujarían fuera de lugar, así que ahí no se pintan.
            <PanZoom key={revision}>
              {demoLayers}
              {frame && selected && !realObject && (
                <TrailLayer frame={frame} points={track} t={clock.t} />
              )}
              {frame && <MarkerLayer frame={frame} markers={realObject ? [] : markers} />}
            </PanZoom>
          )}
        </>
      }
      controls={
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {message && <Typography sx={{ color: "#fff" }}>{message}</Typography>}
          {outside && !skyMode && (
            <Typography variant="body2" sx={{ color: "#fff" }}>
              Ese punto está fuera de esta imagen.
            </Typography>
          )}
          <CollapsiblePanel open={epochsOpen} onToggle={() => setEpochsOpen((o) => !o)}>
            <ModeToggle value={mode} onChange={changeMode} />
            {epochCount > 1 && shownEpochs.length > 1 && (
              <PlaybackBar
                epochs={shownEpochs}
                t={clock.t}
                playing={clock.playing}
                speed={clock.speed}
                onToggle={clock.toggle}
                onSeek={clock.seek}
                onSpeed={clock.setSpeed}
              />
            )}
          </CollapsiblePanel>
          <CollapsiblePanel open={filtersOpen} onToggle={() => setFiltersOpen((o) => !o)}>
            <ControlPanel
              filters={FILTERS}
              current={filterIndex}
              onSelect={setFilterIndex}
              intensityDisabled={filter.fn === null}
              inten={inten}
              gain={gain}
              onInten={setInten}
              onGain={setGain}
              onUpload={() =>
                setSceneError("En la vista previa se usan las épocas simuladas; no se pueden subir imágenes.")
              }
              onDemo={() => {}}
              onHelp={() => {
                setMenuSection(1);
                setMenuOpen(true);
              }}
              isDemo={false}
            />
          </CollapsiblePanel>
        </Box>
      }
      filterLabel={`${filter.name} · ${filter.band}`}
      sourceLabel={
        realObject
          ? `Vista previa · SPHEREx / IRSA · ${realObject.positions.length} épocas reales`
          : "Vista previa · Imágenes simuladas (3 épocas)"
      }
      tagline={<PreviewCredit />}
      menuOpen={menuOpen}
      onOpenMenu={() => {
        setMenuSection(menuSection ?? 0);
        setMenuOpen(true);
      }}
      overlays={
        <>
          <SvgDefs />
          <TopRightTools
            onPickRegion={(ra, dec, fovDeg) => {
              setSelected(null);
              setMarker(null);
              setOutside(false);
              changeMode("sky");
              goSky(ra, dec, fovDeg);
            }}
            objects={objects}
            value={selectValue}
            onPickCandidate={(id) => {
              const obj = objects.find((o) => o.id === id);
              if (obj) pickCandidate(obj);
            }}
            onSearch={search}
            onReset={resetViewer}
            onInfo={() => {
              setMenuSection(0);
              setMenuOpen(true);
            }}
            disabled={!frame}
          />
          {selected && cardOpen && (
            <PreviewCard object={selected} epochs={shownEpochs} onClose={() => setCardOpen(false)} />
          )}
          <MenuDrawer
            open={menuOpen}
            onClose={() => setMenuOpen(false)}
            section={menuSection}
            onSection={setMenuSection}
            filters={FILTERS}
            activeFilter={filterIndex}
            sourceLabel="Vista previa"
          />
          <Snackbar
            open={sceneError !== null}
            autoHideDuration={5000}
            onClose={(_, reason) => {
              if (reason !== "clickaway") setSceneError(null);
            }}
            anchorOrigin={{ vertical: "top", horizontal: "center" }}
          >
            <Alert severity="error" variant="filled" onClose={() => setSceneError(null)}>
              {sceneError}
            </Alert>
          </Snackbar>
        </>
      }
    />
  );
}