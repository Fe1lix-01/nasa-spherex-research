"use client";

import { useRef, type ChangeEvent } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import FileUploadOutlined from "@mui/icons-material/FileUploadOutlined";
import HelpOutlined from "@mui/icons-material/HelpOutlined";
import { eter } from "@/theme/theme";
import type { ControlOption } from "../types";
import FilterChips from "./FilterChips";
import LabeledSlider from "./LabeledSlider";

// Estilo de los botones discretos (Ayuda, Escena demo). Está fuera del componente
// para que no se vuelva a crear en cada render.
const quietButton = {
  minWidth: 0,
  fontSize: { xs: 13, sm: 14 },
  color: "rgba(255,255,255,0.6)",
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
        borderRadius: "28px",
        border: `1px solid ${eter.line}`,
        backgroundColor: "rgba(10,15,22,0.9)",
        backgroundImage: "none",
        backdropFilter: "blur(24px)",
        boxShadow: "0 25px 50px -12px rgba(0,0,0,0.5)",
        p: { xs: 2.5, sm: 3 },
      }}
    >
      <FilterChips options={filters} current={current} onSelect={onSelect} />

      <Divider sx={{ my: 2.5 }} />

      {/* Sliders */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: { xs: 2.5, sm: 4 },
        }}
      >
        <LabeledSlider
          label="Aplicación del filtro"
          value={inten}
          min={0}
          max={100}
          disabled={intensityDisabled}
          onChange={onInten}
        />
        <LabeledSlider label="Intensidad de luz" value={gain} min={10} max={300} onChange={onGain} />
      </Box>

      {/* Ayuda · Subir imagen · Escena demo */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr",
          alignItems: "center",
          gap: 1,
          mt: 2.5,
        }}
      >
        <Button color="inherit" startIcon={<HelpOutlined />} onClick={onHelp} sx={{ ...quietButton, justifySelf: "start" }}>
          Ayuda
        </Button>

        <Button
          variant="outlined"
          color="inherit"
          startIcon={<FileUploadOutlined />}
          onClick={() => fileRef.current?.click()}
          sx={{
            borderRadius: "12px",
            borderColor: eter.lineStrong,
            fontSize: { xs: 13, sm: 14 },
            px: { xs: 1.5, sm: 2 },
            "&:hover": { borderColor: "rgba(255,255,255,0.3)", backgroundColor: "rgba(255,255,255,0.05)" },
          }}
        >
          Subir imagen
        </Button>
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleFile} />

        <Button
          color="inherit"
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
          sx={{ ...quietButton, justifySelf: "end", color: "rgba(255,255,255,0.7)" }}
        >
          Escena demo
        </Button>
      </Box>
    </Paper>
  );
}