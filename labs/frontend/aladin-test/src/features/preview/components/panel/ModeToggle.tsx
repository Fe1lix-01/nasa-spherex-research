"use client";

import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import { eter } from "@/theme/theme";

export type ViewMode = "sky" | "epochs";

type Props = {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
};

/** Cambia entre el mosaico del cielo (Aladin) y las épocas simuladas con animación. */
export default function ModeToggle({ value, onChange }: Props) {
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={value}
      onChange={(_, next: ViewMode | null) => {
        if (next !== null) onChange(next);
      }}
      aria-label="Modo de vista"
      sx={{ alignSelf: "flex-start", bgcolor: eter.panelGlass, backdropFilter: "blur(10px)" }}
    >
      {(
        [
          ["sky", "Mosaico del cielo"],
          ["epochs", "Épocas simuladas"],
        ] as const
      ).map(([mode, label]) => (
        <ToggleButton
          key={mode}
          value={mode}
          sx={{
            px: 1.5,
            py: 0.5,
            fontSize: 13,
            color: eter.textMuted,
            borderColor: eter.lineStrong,
            "&.Mui-selected": { color: eter.accent, bgcolor: eter.accentGlow },
          }}
        >
          {label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
