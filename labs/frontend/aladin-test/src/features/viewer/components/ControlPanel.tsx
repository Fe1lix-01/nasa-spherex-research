"use client";

import { useRef, type ChangeEvent } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import FileUploadOutlined from "@mui/icons-material/FileUploadOutlined";
import HelpOutlined from "@mui/icons-material/HelpOutlined";
import { eter, glassPanel } from "@/theme/theme";
import type { ControlOption } from "../types";
import FilterChips from "./FilterChips";
import LabeledSlider from "./LabeledSlider";
import AnimatedButton from "@/components/AnimatedButton/AnimatedButton";

// Estilo de los botones discretos (Ayuda, Escena demo). Está fuera del componente
// para que no se vuelva a crear en cada render.
const quietButton = {
  minWidth: 0,
  fontSize: { xs: 13, sm: 14 },
  color: eter.textMuted,
  "&:hover": { color: "#fff", backgroundColor: "transparent" },
} as const;

type Props = {
  /** Opciones que se muestran como chips (hoy los filtros de luz). */
  filters: ControlOption[];
  current: number;
  onSelect: (index: number) => void;
  /** Desactiva el slider "Aplicación del filtro" (p. ej. cuando no hay filtro activo). */
  intensityDisabled: boolean;
  inten: number;
  gain: number;
  onInten: (value: number) => void;
  onGain: (value: number) => void;
  onUpload: (file: File) => void;
  onDemo: () => void;
  onHelp: () => void;
  isDemo: boolean;
};

export default function ControlPanel({
  filters,
  current,
  onSelect,
  intensityDisabled,
  inten,
  gain,
  onInten,
  onGain,
  onUpload,
  onDemo,
  onHelp,
  isDemo,
}: Props) {
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = ""; // permite subir el mismo archivo otra vez
  };

  return (
    <Paper
      component="section"
      aria-label="Controles del visor"
      elevation={0}
      sx={{
        ...glassPanel,
        borderRadius: { xs: "18px", lg: "999px" },
        // MUI agrega un degradado claro a los Paper en modo oscuro; se anula para
        // que el vidrio se vea parejo.
        backgroundImage: "none",
        px: { xs: 1.5, lg: 2.5 },
        py: { xs: 1, lg: 0.75 },
        // Barra delgada: en pantallas grandes todo va en una sola fila.
        display: "flex",
        flexDirection: { xs: "column", lg: "row" },
        alignItems: { xs: "stretch", lg: "center" },
        gap: { xs: 1, lg: 2.5 },
      }}
    >
      <Box sx={{ minWidth: 0, flex: { lg: "1 1 auto" } }}>
        <FilterChips options={filters} current={current} onSelect={onSelect} />
      </Box>

      {/* Sliders */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: { xs: 2, lg: 3 },
          flex: { lg: "0 0 340px" },
        }}
      >
        <LabeledSlider
          compact
          label="Aplicación del filtro"
          value={inten}
          min={0}
          max={100}
          disabled={intensityDisabled}
          onChange={onInten}
        />
        <LabeledSlider compact label="Intensidad de luz" value={gain} min={10} max={300} onChange={onGain} />
      </Box>

      {/* Ayuda · Subir imagen · Escena demo */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 0.5 }}>
        <Button
          color="inherit"
          size="small"
          startIcon={<HelpOutlined />}
          onClick={onHelp}
          sx={{ ...quietButton, fontSize: 12 }}
        >
          Ayuda
        </Button>

        <AnimatedButton onClick={() => fileRef.current?.click()}>
          <FileUploadOutlined sx={{ fontSize: 18 }} />
          Subir imagen
        </AnimatedButton>

        <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleFile} />

        <Button
          color="inherit"
          size="small"
          onClick={onDemo}
          // Indica a lectores de pantalla si la escena demo es la que está activa.
          aria-pressed={isDemo}
          startIcon={
            <Box
              component="span"
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: isDemo ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.25)",
              }}
            />
          }
          sx={{ ...quietButton, fontSize: 12, whiteSpace: "nowrap", color: "rgba(255,255,255,0.7)" }}
        >
          Escena demo
        </Button>
      </Box>
    </Paper>
  );
}