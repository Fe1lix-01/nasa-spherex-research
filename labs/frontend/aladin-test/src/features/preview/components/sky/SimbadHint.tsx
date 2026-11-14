"use client";

import Box from "@mui/material/Box";
import { eter } from "@/theme/theme";

/**
 * Aviso que sigue al cursor cuando pasa sobre un objeto de SIMBAD.
 * Solo dice que hay información: los datos completos van en la tarjeta que se abre al hacer clic.
 * `pointerEvents: none` evita que el aviso se meta entre el cursor y la marca (si no, parpadearía).
 */
export default function SimbadHint({ x, y }: { x: number; y: number }) {
  return (
    <Box
      role="tooltip"
      sx={{
        position: "absolute",
        left: x + 16,
        top: y + 18,
        px: 1.5,
        py: 0.75,
        borderRadius: "10px",
        fontSize: 12.5,
        letterSpacing: "0.02em",
        color: "rgba(255,255,255,0.92)",
        whiteSpace: "nowrap",
        background: "rgba(12,18,28,0.72)",
        backdropFilter: "blur(14px) saturate(140%)",
        WebkitBackdropFilter: "blur(14px) saturate(140%)",
        border: `1px solid ${eter.lineStrong}`,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 24px rgba(0,0,0,0.35)",
        pointerEvents: "none",
        animation: "simbadHintIn 120ms ease-out",
        "@keyframes simbadHintIn": {
          from: { opacity: 0, transform: "translateY(3px)" },
          to: { opacity: 1, transform: "none" },
        },
      }}
    >
      Información sobre este objeto
    </Box>
  );
}