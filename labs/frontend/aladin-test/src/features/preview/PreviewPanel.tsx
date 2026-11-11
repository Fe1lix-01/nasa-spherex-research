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
import MarkerLayer, { type Marker } from "./components/MarkerLayer";
import PreviewCard from "./components/PreviewCard";
import { matchObject } from "./objectsMatch";
import { skyToImage } from "./projection";
import PanZoom from "./components/PanZoom";
import CollapsiblePanel from "./components/CollapsiblePanel";
import TopRightTools from "./components/TopRightTools";
import PreviewCredit from "./components/PreviewCredit";
import EpochLayer from "./components/EpochLayer";
import PlaybackBar from "./components/PlaybackBar";
import TrailLayer from "./components/TrailLayer";
import ModeToggle, { type ViewMode } from "./components/ModeToggle";
import SkyStage from "./components/SkyStage";
import { skyCssFilter } from "./components/skyFilters";
import { useEpochClock } from "./hooks/useEpochClock";
import { positionAt, trackPoints } from "./trajectory";

/** A dónde mira el mosaico. `nonce` cambia en cada búsqueda para volver a ir aunque sea al mismo punto. */
type SkyTarget = { raDeg: number; decDeg: number; fovDeg: number; nonce: number };
const ALL_SKY: SkyTarget = { raDeg: 0, decDeg: 0, fovDeg: 360, nonce: 0 };
const CLOSE_UP_FOV_DEG = 1.5; // campo al ir a un candidato o a unas coordenadas
const TEST_LABEL = "Prueba"; // nombre de la zona con imágenes simuladas

/**
 * Opacidad de la capa de la época i en el instante t. La primera siempre está debajo y
 * opaca; cada una de las siguientes aparece de forma gradual cuando t llega a su época.
 */
const layerOpacity = (i: number, t: number) => (i === 0 ? 1 : Math.min(Math.max(t - (i - 1), 0), 1));

/**
 * Vista previa de movimiento dentro del visor de ÉTER. Tiene dos modos:
 *  - Mosaico del cielo: el mapa interactivo de Aladin (AllWISE como referencia). Las imágenes
 *    simuladas ("Prueba") se pintan encima, en la zona del cielo donde están los objetos de
 *    prueba, con los mismos filtros, marcador, rastro y animación.
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
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [revision, setRevision] = useState(0);
  const [mode, setMode] = useState<ViewMode>("epochs");
  const [skyTarget, setSkyTarget] = useState<SkyTarget>(ALL_SKY);
  const [skyOpened, setSkyOpened] = useState(false); // el mapa se crea la primera vez que se entra
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

  const clock = useEpochClock(frames?.length ?? 0, 3);
  const frame = frames?.[0] ?? null;
  const filter = FILTERS[filterIndex];
  const skyMode = mode === "sky";

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
  };

  const pickCandidate = (obj: MovingObject) => {
    if (!frame) return;
    const first = trackPoints(obj, epochs)[0];
    if (!first) return;
    setOutside(skyToImage(first.ra, first.dec, frame) === null);
    setMarker(null); // el marcador del candidato lo dibuja la animación
    goSky(first.ra, first.dec, CLOSE_UP_FOV_DEG);
    setSelected(obj);
    clock.seek(0);
  };

  const message = loadError ?? (!frame ? "Cargando imágenes…" : null);

  // Lo que muestra el selector de arriba: el candidato elegido, o "custom" si buscaron coordenadas.
  const selectValue = selected?.id ?? (marker ? "custom" : "");

  // Marcadores: el de las coordenadas buscadas (fijo) y el del candidato (se mueve con t).
  const markers: Marker[] = [];
  if (marker) markers.push(marker);
  const moving = selected ? positionAt(selected, epochs, clock.t) : null;
  if (selected && moving) {
    markers.push({ id: `${selected.id}-now`, label: selected.name ?? selected.id, ...moving });
  }
  const trail = selected ? trackPoints(selected, epochs) : [];

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

  // Las imágenes de prueba: se usan a pantalla completa o dentro del mosaico, según el modo.
  const epochLayers = frames?.map((f, i) => (
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

  return (
    <ViewerShell
      background={
        <>
          {skyOpened && !skyFailed && (
            <SkyStage
              active={skyMode}
              target={skyTarget}
              cssFilter={skyCssFilter(filter.id, inten, gain)}
              patch={{
                ra: frame?.ra ?? 209.4201,
                dec: frame?.dec ?? 53.9431,
                fovDeg: frame?.fovDeg ?? 3.5,
                label: TEST_LABEL,
              }}
              patchContent={skyMode ? epochLayers : null}
              markers={markers}
              trail={trail}
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
            <PanZoom key={revision}>
              {epochLayers}
              {frame && selected && <TrailLayer frame={frame} points={trail} t={clock.t} />}
              {frame && <MarkerLayer frame={frame} markers={markers} />}
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
          <ModeToggle value={mode} onChange={changeMode} />
          {frames && frames.length > 1 && epochs.length > 1 && (
            <PlaybackBar
              epochs={epochs}
              t={clock.t}
              playing={clock.playing}
              speed={clock.speed}
              onToggle={clock.toggle}
              onSeek={clock.seek}
              onSpeed={clock.setSpeed}
            />
          )}
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
      sourceLabel="Vista previa · Imágenes simuladas (3 épocas)"
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
          {selected && (
            <PreviewCard object={selected} epochs={epochs} onClose={() => setSelected(null)} />
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
