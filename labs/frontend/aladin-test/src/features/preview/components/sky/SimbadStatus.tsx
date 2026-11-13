"use client";

import Box from "@mui/material/Box";
import { eter } from "@/theme/theme";
import type { SimbadLayerStatus } from "./useSimbadLayer";

/**
 * Aviso del estado de la capa SIMBAD, arriba al centro del mapa. Solo aparece cuando hay algo que
 * decirle a la persona: que el campo es muy ancho (por eso no hay círculos) o que falló la consulta.
 */
export default function SimbadStatus({ status }: { status: SimbadLayerStatus }) {
  const text =
    status === "wide" ? "Acércate para ver objetos" : status === "error" ? "No se pudo consultar SIMBAD" : null;
  if (!text) return null;

  return (
    <Box
      role="status"
      sx={{
        position: "absolute",
        left: "50%",
        top: 16,
        transform: "translateX(-50%)",
        px: 2,
        py: 0.75,
        borderRadius: "999px",
        fontSize: 13,
        color: status === "error" ? eter.danger : "rgba(255,255,255,0.92)",
        whiteSpace: "nowrap",
        background: "rgba(12,18,28,0.72)",
        backdropFilter: "blur(14px) saturate(140%)",
        WebkitBackdropFilter: "blur(14px) saturate(140%)",
        border: `1px solid ${eter.lineStrong}`,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 24px rgba(0,0,0,0.35)",
        pointerEvents: "none",
        animation: "simbadStatusIn 200ms ease-out",
        "@keyframes simbadStatusIn": { from: { opacity: 0 }, to: { opacity: 1 } },
        "@media (prefers-reduced-motion: reduce)": { animation: "none" },
      }}
    >
      {text}
    </Box>
  );
}