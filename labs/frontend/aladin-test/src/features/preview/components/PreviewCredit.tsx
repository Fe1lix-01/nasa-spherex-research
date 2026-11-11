"use client";

import { useState } from "react";
import Typography from "@mui/material/Typography";

/**
 * Crédito del proyecto, pequeño, abajo a la izquierda. Al tocarlo desaparece.
 */
export default function PreviewCredit() {
  const [visible, setVisible] = useState(true);
  if (!visible) return null;

  return (
    <Typography
      role="button"
      tabIndex={0}
      title="Toca para ocultar"
      onClick={() => setVisible(false)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") setVisible(false);
      }}
      sx={{
        pointerEvents: "auto",
        cursor: "pointer",
        alignSelf: "flex-start",
        fontSize: 11,
        letterSpacing: "0.04em",
        color: "rgba(255,255,255,0.6)",
        textShadow: "0 1px 8px rgba(0,0,0,0.7)",
        "&:hover": { color: "rgba(255,255,255,0.9)" },
      }}
    >
      Proyecto realizado por alumnos del TecNM
    </Typography>
  );
}