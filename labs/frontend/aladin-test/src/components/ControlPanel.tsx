"use client";

import { useId, useRef, type ChangeEvent } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";
import FileUploadOutlined from "@mui/icons-material/FileUploadOutlined";
import HelpOutlined from "@mui/icons-material/HelpOutlined";
import type { FilterDef } from "@/lib/types";
import { eter } from "@/theme/theme";

/* ---------- Slider con etiqueta, valor ámbar y límites (como en Figma) ---------- */

type LabeledSliderProps = {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  onChange: (value: number) => void;
};

function LabeledSlider({ label, value, min, max, disabled, onChange }: LabeledSliderProps) {
  const labelId = useId();
  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <Typography id={labelId} sx={{ fontSize: 15, color: "rgba(255,255,255,0.9)" }}>
          {label}
        </Typography>
        <Typography sx={{ fontSize: 14, fontWeight: 500, color: "primary.main" }}>{value} %</Typography>
      </Box>

      <Slider
        aria-labelledby={labelId}
        value={value}
        min={min}
        max={max}
        disabled={disabled}
        valueLabelDisplay="off"
        // MUI entrega number | number[]; aquí siempre es un solo valor.
        onChange={(_, v) => onChange(Array.isArray(v) ? v[0] : v)}
        sx={{
          height: 2,
          mt: 0.5,
          "& .MuiSlider-rail": { opacity: 1, backgroundColor: "rgba(255,255,255,0.16)" },
          "& .MuiSlider-track": { border: "none", height: 2 },
          "& .MuiSlider-thumb": {
            width: 14,
            height: 14,
            boxShadow: "0 0 0 4px rgba(255,210,76,0.18)",
            "&::before": { boxShadow: "none" },
            "&:hover, &.Mui-focusVisible": { boxShadow: "0 0 0 7px rgba(255,210,76,0.28)" },
          },
          "&.Mui-disabled": { color: "primary.main", opacity: 0.35 },
        }}
      />

      <Box sx={{ display: "flex", justifyContent: "space-between", mt: -0.5 }}>
        <Typography variant="caption" sx={{ color: "text.disabled" }}>
          {min} %
        </Typography>
        <Typography variant="caption" sx={{ color: "text.disabled" }}>
          {max} %
        </Typography>
      </Box>
    </Box>
  );
}

/* ---------- Panel ---------- */

type Props = {
  filters: FilterDef[];
  current: number;
  onSelect: (index: number) => void;
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
  const hasFilter = filters[current].fn !== null;

  const handleFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = ""; // permite subir el mismo archivo otra vez
  };

  const quietButton = {
    minWidth: 0,
    fontSize: { xs: 13, sm: 14 },
    color: "rgba(255,255,255,0.6)",
    "&:hover": { color: "#fff", backgroundColor: "transparent" },
  } as const;

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
      {/* Filtros de luz (uno activo a la vez, con scroll horizontal en pantallas pequeñas) */}
      <Box
        role="group"
        aria-label="Filtros de luz"
        sx={{
          display: "flex",
          gap: 1.25,
          overflowX: "auto",
          mx: -0.5,
          px: 0.5,
          pb: 0.5,
          scrollbarWidth: "none",
          "&::-webkit-scrollbar": { display: "none" },
        }}
      >
        {filters.map((f, i) => {
          const on = i === current;
          return (
            <Chip
              key={f.id}
              label={f.name}
              clickable
              aria-pressed={on}
              onClick={() => onSelect(i)}
              variant={on ? "filled" : "outlined"}
              sx={{
                flexShrink: 0,
                height: 44,
                borderRadius: "999px",
                fontSize: 15,
                "& .MuiChip-label": { px: 2.5 },
                ...(on
                  ? {
                      backgroundColor: eter.accent,
                      borderColor: eter.accent,
                      color: "#000",
                      fontWeight: 500,
                      "&:hover": { backgroundColor: eter.accent },
                    }
                  : {
                      borderColor: eter.lineStrong,
                      color: "rgba(255,255,255,0.6)",
                      "&:hover": {
                        backgroundColor: "transparent",
                        borderColor: "rgba(255,255,255,0.3)",
                        color: "#fff",
                      },
                    }),
              }}
            />
          );
        })}
      </Box>

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
          disabled={!hasFilter}
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
