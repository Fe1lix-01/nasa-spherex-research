"use client";

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import { CrosshairIcon } from "@/components/icons/CustomIcons";
import ViewerHeader from "./ViewerHeader";
import ViewerTagline from "./ViewerTagline";

type Props = {
  /** Fondo a pantalla completa: el canvas con filtros, el mosaico de Aladin, etc. */
  background: ReactNode;
  /** Panel de controles que va abajo. */
  controls: ReactNode;
  /** Elementos que flotan sobre todo: menú lateral, avisos... */
  overlays?: ReactNode;
  /** Texto del chip del encabezado, por ejemplo "Visible · 0.38–0.75 µm". */
  filterLabel: string;
  /** Texto bajo la frase, por ejemplo "Escena demo". */
  sourceLabel: string;
  menuOpen: boolean;
  onOpenMenu: () => void;
};

/**
 * Marco de diseño de ÉTER: encabezado, frase y panel de controles sobre un fondo
 * intercambiable. El fondo solo necesita llenar el 100 % de su contenedor.
 */
export default function ViewerShell({
  background,
  controls,
  overlays,
  filterLabel,
  sourceLabel,
  menuOpen,
  onOpenMenu,
}: Props) {
  return (
    <Box component="main" sx={{ position: "relative", height: "100%", width: "100%", overflow: "hidden" }}>
      {/* Fondo: ocupa toda la pantalla */}
      <Box sx={{ position: "absolute", inset: 0 }}>{background}</Box>

      {/* Sombras suaves para que el texto se lea sobre cualquier imagen */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          background: "linear-gradient(to bottom, rgba(0,0,0,0.5), transparent 30%, transparent 60%, rgba(0,0,0,0.5))",
        }}
      />

      {/* Retícula central */}
      <CrosshairIcon
        sx={{
          pointerEvents: "none",
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          fontSize: 28,
          color: "rgba(255,255,255,0.4)",
        }}
      />

      <ViewerHeader filterLabel={filterLabel} menuOpen={menuOpen} onOpenMenu={onOpenMenu} />

      {/* Zona inferior: frase + panel de controles */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: { lg: "center" },
          p: { xs: 2, sm: 3 },
          pb: { xs: "max(16px, env(safe-area-inset-bottom))", lg: 5 },
        }}
      >
        <Box
          sx={{
            width: { xs: "100%", lg: "56%" },
            maxWidth: { lg: 896 },
            display: "flex",
            flexDirection: "column",
            gap: 2,
          }}
        >
          <ViewerTagline sourceLabel={sourceLabel} />
          <Box sx={{ pointerEvents: "auto" }}>{controls}</Box>
        </Box>
      </Box>

      {overlays}
    </Box>
  );
}