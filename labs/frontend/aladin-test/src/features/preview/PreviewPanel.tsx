"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Frame } from "@/contracts";
import ViewerShell from "@/features/viewer/components/ViewerShell";
import { skyData } from "@/services";
import CoordinateForm from "./components/CoordinateForm";
import FrameView, { type Marker } from "./components/FrameView";
import { skyToImage } from "./projection";

/**
 * Vista previa de movimiento, dentro del mismo marco visual de ÉTER (ViewerShell).
 * La imagen va de fondo y el formulario de coordenadas en el panel de controles.
 */
export default function PreviewPanel() {
  const [frames, setFrames] = useState<Frame[] | null>(null);
  const [marker, setMarker] = useState<Marker | null>(null);
  const [outside, setOutside] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    skyData
      .getFrames()
      .then(setFrames)
      .catch(() => setLoadError("No se pudieron cargar las imágenes."));
  }, []);

  const message = loadError ?? (!frames ? "Cargando imágenes…" : null);
  // Por ahora usamos la primera época; la animación recorrerá todas.
  const frame = frames?.[0] ?? null;

  const search = (ra: number, dec: number) => {
    if (!frame) return;
    setOutside(skyToImage(ra, dec, frame) === null);
    setMarker({ id: `${ra},${dec}`, label: `${ra.toFixed(4)}, ${dec.toFixed(4)}`, ra, dec });
  };

  return (
    <ViewerShell
      background={frame ? <FrameView frame={frame} markers={marker ? [marker] : []} /> : <Box sx={{ position: "absolute", inset: 0, bgcolor: "#000" }} />}
      controls={
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {message && <Typography sx={{ color: "#fff" }}>{message}</Typography>}
          {frame && <CoordinateForm onSearch={search} />}
          {outside && (
            <Typography variant="body2" sx={{ color: "#fff" }}>
              Ese punto está fuera de esta imagen.
            </Typography>
          )}
        </Box>
      }
      filterLabel="Vista previa · Época 1"
      sourceLabel="Imagen SPHEREx · 2025W19"
      menuOpen={false}
      onOpenMenu={() => {}}
    />
  );
}
