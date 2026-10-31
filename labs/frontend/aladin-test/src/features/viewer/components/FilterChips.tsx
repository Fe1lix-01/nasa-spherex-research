"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { eter } from "@/theme/theme";
import type { ControlOption } from "../types";

type Props = {
  options: ControlOption[];
  /** Índice de la opción activa. */
  current: number;
  onSelect: (index: number) => void;
};

/** Fila de chips: uno activo a la vez, con scroll horizontal en pantallas pequeñas. */
export default function FilterChips({ options, current, onSelect }: Props) {
  return (
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
      {options.map((f, i) => {
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
  );
}