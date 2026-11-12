"use client";

import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import type { SxProps, Theme } from "@mui/material/styles";
import { eter } from "@/theme/theme";

type Option<T> = { value: T; label: string };

type Props<T extends string | number> = {
  value: T;
  onChange: (value: T) => void;
  options: readonly Option<T>[];
  ariaLabel: string;
  /** "md" para selectores principales, "sm" para los compactos (p. ej. velocidades). */
  size?: "md" | "sm";
  /** Ajustes de posición o fondo que dependen de dónde se coloque el control. */
  sx?: SxProps<Theme>;
};

// Los dos tamaños viven aquí para que ningún componente repita estos números.
const SIZES = {
  md: { px: 1.5, py: 0.5, fontSize: 13 },
  sm: { px: 1, py: 0.25, fontSize: 12 },
} as const;

/**
 * Selector de una sola opción (estilo "pastillas pegadas"). Lo usan el cambio de modo
 * de vista y la velocidad de reproducción, para que se vean y se comporten igual.
 */
export default function SegmentedControl<T extends string | number>({
  value,
  onChange,
  options,
  ariaLabel,
  size = "md",
  sx,
}: Props<T>) {
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={value}
      // MUI manda null al volver a pulsar la opción activa; se ignora para que
      // siempre quede una opción elegida.
      onChange={(_, next: T | null) => {
        if (next !== null) onChange(next);
      }}
      aria-label={ariaLabel}
      sx={sx}
    >
      {options.map((option) => (
        <ToggleButton
          key={option.value}
          value={option.value}
          sx={{
            ...SIZES[size],
            color: eter.textMuted,
            borderColor: eter.lineStrong,
            "&:hover": { backgroundColor: eter.hoverFill },
            "&.Mui-selected": { color: eter.accent, backgroundColor: eter.accentGlow },
            "&.Mui-selected:hover": { backgroundColor: eter.accentGlowStrong },
            // Foco hacia adentro: si fuera hacia afuera, el botón vecino lo taparía.
            "&:focus-visible": { outline: `2px solid ${eter.focusRing}`, outlineOffset: -2 },
          }}
        >
          {option.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}