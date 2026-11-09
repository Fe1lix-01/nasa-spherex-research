"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import type { Epoch, Frame, MovingObject } from "@/contracts";
import ControlPanel from "@/features/viewer/components/ControlPanel";
import ViewerCanvas from "@/features/viewer/components/ViewerCanvas";
import ViewerShell from "@/features/viewer/components/ViewerShell";
import MenuDrawer from "@/features/menu/MenuDrawer";
import { SvgDefs } from "@/features/phenomena/SvgDefs";
import { FILTERS } from "@/features/viewer/engine/filters";
import { useSpectralScene } from "@/features/viewer/hooks/useSpectralScene";
import { skyData } from "@/services";
import CoordinateForm from "./components/CoordinateForm";
import MarkerLayer, { type Marker } from "./components/MarkerLayer";
import PreviewCard from "./components/PreviewCard";
import CandidateList from "./components/CandidateList";
import { matchObject } from "./objectsMatch";
import { skyToImage } from "./projection";

/**
 * Vista previa de movimiento dentro del visor de ÉTER: mismo canvas, mismos filtros y
 * controles. La imagen de la época va como escena, y los objetos se marcan por coordenadas.
 *
 * Al buscar las coordenadas de un candidato (o al elegirlo de la lista) aparece un
 * recuadro flotante con la información básica y la estructura lista para las 3 épocas.
 */
export default function PreviewPanel() {
  const [frames, setFrames] = useState<Frame[] | null>(null);
  const [objects, setObjects] = useState<MovingObject[]>([]);
  const [epochs, setEpochs] = useState<Epoch[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filterIndex, setFilterIndex] = useState(0);
  const [inten, setInten] = useState(72);
  const [gain, setGain] = useState(110);
  const [marker, setMarker] = useState<Marker | null>(null);
  const [outside, setOutside] = useState(false);
  const [selected, setSelected] = useState<MovingObject | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);

  useEffect(() => {
    Promise.all([skyData.getFrames(), skyData.getObjects(), skyData.getEpochs()])
      .then(([f, o, e]) => {
        setFrames(f);
        setObjects(o.objects);
        setEpochs(e);
      })
      .catch(() => setLoadError("No se pudieron cargar los datos de la vista previa."));
  }, []);

  // Por ahora usamos la primera época; la animación recorrerá todas cuando lleguen.
  const frame = frames?.[0] ?? null;
  const filter = FILTERS[filterIndex];
  const { canvasRef, error, clearError, upload } = useSpectralScene(filter, inten, gain, frame?.imageUrl);

  const search = (ra: number, dec: number) => {
    if (!frame) return;
    setOutside(skyToImage(ra, dec, frame) === null);
    setMarker({ id: `${ra},${dec}`, label: `${ra.toFixed(4)}, ${dec.toFixed(4)}`, ra, dec });
    // Si las coordenadas caen cerca de un candidato (0.5°), abrimos su recuadro.
    setSelected(matchObject(ra, dec, objects, 0.5));
  };

  const pickCandidate = (obj: MovingObject) => {
    if (!frame) return;
    const last = obj.positions[obj.positions.length - 1];
    if (!last) return;
    setOutside(skyToImage(last.ra, last.dec, frame) === null);
    setMarker({ id: obj.id, label: obj.name ?? obj.id, ra: last.ra, dec: last.dec });
    setSelected(obj);
  };

  const message = loadError ?? (!frame ? "Cargando imágenes…" : null);

  return (
    <ViewerShell
      background={
        <>
          <ViewerCanvas canvasRef={canvasRef} />
          {frame && <MarkerLayer frame={frame} markers={marker ? [marker] : []} />}
        </>
      }
      controls={
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {message && <Typography sx={{ color: "#fff" }}>{message}</Typography>}
          {frame && <CoordinateForm onSearch={search} />}
          {frame && objects.length > 0 && <CandidateList objects={objects} onSelect={pickCandidate} />}
          {outside && (
            <Typography variant="body2" sx={{ color: "#fff" }}>
              Ese punto está fuera de esta imagen.
            </Typography>
          )}
          <ControlPanel
            filters={FILTERS}
            current={filterIndex}
            onSelect={setFilterIndex}
            intensityDisabled={filter.fn === null}
            inten={inten}
            gain={gain}
            onInten={setInten}
            onGain={setGain}
            onUpload={(file) => {
              clearError();
              upload(file);
            }}
            onDemo={() => {}}
            onHelp={() => {
              setMenuSection(1);
              setMenuOpen(true);
            }}
            isDemo={false}
          />
        </Box>
      }
      filterLabel={`${filter.name} · ${filter.band}`}
      sourceLabel="Vista previa · Imagen SPHEREx 2025W19"
      menuOpen={menuOpen}
      onOpenMenu={() => {
        setMenuSection(menuSection ?? 0);
        setMenuOpen(true);
      }}
      overlays={
        <>
          <SvgDefs />
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
            open={error !== null}
            autoHideDuration={5000}
            onClose={(_, reason) => {
              if (reason !== "clickaway") clearError();
            }}
            anchorOrigin={{ vertical: "top", horizontal: "center" }}
          >
            <Alert severity="error" variant="filled" onClose={() => clearError()}>
              {error}
            </Alert>
          </Snackbar>
        </>
      }
    />
  );
}
