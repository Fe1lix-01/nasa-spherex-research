"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import type { Frame } from "@/contracts";
import { skyData } from "@/services";
import CoordinateForm from "./components/CoordinateForm";
import FrameView, { type Marker } from "./components/FrameView";
import { skyToImage } from "./projection";

/**
 * Vista previa de movimiento. Carga las imágenes por época y deja buscar cualquier
 * coordenada para marcarla. Cuando haya varias épocas, aquí se animará la secuencia.
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

  if (loadError) return <Typography color="error">{loadError}</Typography>;
  if (!frames || frames.length === 0) return <Typography>Cargando imágenes…</Typography>;

  // Por ahora usamos la primera época; la animación recorrerá todas.
  const frame = frames[0];

  const search = (ra: number, dec: number) => {
    setOutside(skyToImage(ra, dec, frame) === null);
    setMarker({ id: `${ra},${dec}`, label: `${ra.toFixed(4)}, ${dec.toFixed(4)}`, ra, dec });
  };

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, p: 2 }}>
      <CoordinateForm onSearch={search} />
      <FrameView frame={frame} markers={marker ? [marker] : []} />
      {outside && (
        <Typography variant="body2" sx={{ textAlign: "center" }}>
          Ese punto está fuera de esta imagen.
        </Typography>
      )}
    </Box>
  );
}
