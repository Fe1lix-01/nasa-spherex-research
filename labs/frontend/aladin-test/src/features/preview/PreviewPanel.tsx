"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Frame } from "@/contracts";
import ControlPanel from "@/features/viewer/components/ControlPanel";
import ViewerCanvas from "@/features/viewer/components/ViewerCanvas";
import ViewerShell from "@/features/viewer/components/ViewerShell";
import MenuDrawer from "@/features/menu/MenuDrawer";
import { SvgDefs } from "@/features/phenomena/SvgDefs";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import { FILTERS } from "@/features/viewer/engine/filters";
import { useSpectralScene } from "@/features/viewer/hooks/useSpectralScene";
import { skyData } from "@/services";
import CoordinateForm from "./components/CoordinateForm";
import MarkerLayer, { type Marker } from "./components/MarkerLayer";
import { skyToImage } from "./projection";

/**
 * Vista previa de movimiento dentro del visor de ÉTER: mismo canvas, mismos filtros y
 * controles. La imagen de la época va como escena, y los objetos se marcan por coordenadas.
 */
export default function PreviewPanel() {
  const [frames, setFrames] = useState<Frame[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filterIndex, setFilterIndex] = useState(0);
  const [inten, setInten] = useState(72);
  const [gain, setGain] = useState(110);
  const [marker, setMarker] = useState<Marker | null>(null);
  const [outside, setOutside] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);

  useEffect(() => {
    skyData
      .getFrames()
      .then(setFrames)
      .catch(() => setLoadError("No se pudieron cargar las imágenes."));
  }, []);

  // Por ahora usamos la primera época; la animación recorrerá todas.
  const frame = frames?.[0] ?? null;
  const filter = FILTERS[filterIndex];
  const { canvasRef, error, clearError, upload } = useSpectralScene(filter, inten, gain, frame?.imageUrl);

  const search = (ra: number, dec: number) => {
    if (!frame) return;
    setOutside(skyToImage(ra, dec, frame) === null);
    setMarker({ id: `${ra},${dec}`, label: `${ra.toFixed(4)}, ${dec.toFixed(4)}`, ra, dec });
  };

  const message = loadError ?? (!frame ? "Cargando imágenes…" : error);

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
