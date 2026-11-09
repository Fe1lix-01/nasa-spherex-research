"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { MovingObject } from "@/contracts";
import { KIND_LABELS } from "../labels";

type Props = {
  objects: MovingObject[];
  onSelect: (obj: MovingObject) => void;
};

/**
 * Lista de chips con los candidatos cargados. Al hacer click se selecciona el objeto
 * y se centra el marcador en su última posición, sin tener que escribir las coordenadas
 * a mano.
 */
export default function CandidateList({ objects, onSelect }: Props) {
  if (objects.length === 0) return null;
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, maxWidth: 720, mx: "auto", width: "100%" }}>
      <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.7)" }}>
        Candidatos
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
        {objects.map((obj) => (
          <Chip
            key={obj.id}
            label={`${obj.name ?? obj.id} · ${KIND_LABELS[obj.kind] ?? obj.kind}`}
            onClick={() => onSelect(obj)}
            sx={{
              bgcolor: "rgba(255,255,255,0.08)",
              color: "#fff",
              border: "1px solid rgba(255,213,79,0.3)",
              "&:hover": { bgcolor: "rgba(255,213,79,0.15)" },
            }}
          />
        ))}
      </Box>
    </Box>
  );
}
