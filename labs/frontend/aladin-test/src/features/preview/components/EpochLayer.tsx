"use client";

import { useEffect } from "react";
import Box from "@mui/material/Box";
import ViewerCanvas from "@/features/viewer/components/ViewerCanvas";
import { useSpectralScene } from "@/features/viewer/hooks/useSpectralScene";
import type { FilterDef } from "@/features/viewer/types";

type Props = {
  imageUrl: string;
  filter: FilterDef;
  inten: number;
  gain: number;
  /** 0 = invisible, 1 = totalmente visible. Lo controla la animación. */
  opacity: number;
  onError: (message: string | null) => void;
};

/**
 * Una época como capa propia: su canvas con los mismos filtros del visor. Cada época
 * mantiene su imagen cargada todo el tiempo, y la animación solo cambia la opacidad,
 * así no hay recargas ni parpadeos al pasar de una a otra.
 */
export default function EpochLayer({ imageUrl, filter, inten, gain, opacity, onError }: Props) {
  const { canvasRef, error } = useSpectralScene(filter, inten, gain, imageUrl);

  useEffect(() => {
    if (error) onError(error);
  }, [error, onError]);

  return (
    <Box sx={{ position: "absolute", inset: 0, opacity }}>
      <ViewerCanvas canvasRef={canvasRef} />
    </Box>
  );
}
