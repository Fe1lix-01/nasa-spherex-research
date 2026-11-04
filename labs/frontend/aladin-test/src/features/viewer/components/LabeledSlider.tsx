"use client";

import { useId } from "react";
import Box from "@mui/material/Box";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";
import { eter } from "@/theme/theme";

type Props = {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  onChange: (value: number) => void;
};

/** Slider con etiqueta, valor en ámbar y límites mínimo y máximo. */
export default function LabeledSlider({ label, value, min, max, disabled, onChange }: Props) {
  // useId liga la etiqueta con el slider para que los lectores de pantalla lo anuncien.
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
        getAriaValueText={(v) => `${v} %`}
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
          "& .MuiSlider-rail": { opacity: 1, backgroundColor: eter.rail },
          "& .MuiSlider-track": { border: "none", height: 2 },
          "& .MuiSlider-thumb": {
            width: 14,
            height: 14,
            boxShadow: '0 0 0 4px ${eter.accentGlow}',
            "&::before": { boxShadow: "none" },
            "&:hover, &.Mui-focusVisible": { boxShadow: '0 0 0 7px ${eter.accentGlowStrong}' },
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