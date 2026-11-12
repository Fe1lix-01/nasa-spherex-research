"use client";

import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import KeyboardArrowDown from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUp from "@mui/icons-material/KeyboardArrowUp";
import { eter } from "@/theme/theme";

type Props = { open: boolean; onToggle: () => void; children: ReactNode };

/** Panel que se pliega hacia abajo. La flecha queda siempre al centro, abajo. */
export default function CollapsiblePanel({ open, onToggle, children }: Props) {
  return (
    <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <Collapse in={open} sx={{ width: "100%" }}>
        {children}
      </Collapse>
      <IconButton
        onClick={onToggle}
        aria-label={open ? "Ocultar filtros" : "Mostrar filtros"}
        aria-expanded={open}
        sx={{
          mt: 1,
          color: "#fff",
          border: `1px solid ${eter.lineStrong}`,
          backgroundColor: eter.glass,
          backdropFilter: "blur(8px)",
          "&:hover": { borderColor: eter.lineHover, backgroundColor: eter.hoverFill },
          "&:focus-visible": { outline: `2px solid ${eter.focusRing}`, outlineOffset: 2 },       
        }}
      >
        {open ? <KeyboardArrowDown /> : <KeyboardArrowUp />}
      </IconButton>
    </Box>
  );
}