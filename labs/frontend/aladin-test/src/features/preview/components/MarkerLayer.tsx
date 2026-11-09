"use client";

import Box from "@mui/material/Box";
import type { Frame } from "@/contracts";
import { skyToImage } from "../projection";

export type Marker = { id: string; label: string; ra: number; dec: number };

type Props = { frame: Frame; markers: Marker[] };

/**
 * Capa de marcadores encima del canvas del visor. Usa porcentajes, así que se acomoda
 * sola al tamaño de la pantalla, igual que el canvas que se estira a toda la pantalla.
 */
export default function MarkerLayer({ frame, markers }: Props) {
  return (
    <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {markers.map((m) => {
        const p = skyToImage(m.ra, m.dec, frame);
        if (!p) return null;
        return (
          <Box
            key={m.id}
            sx={{
              position: "absolute",
              left: `${p.x * 100}%`,
              top: `${p.y * 100}%`,
              transform: "translate(-50%, -50%)",
              width: 18,
              height: 18,
              border: "2px solid #FFD54F",
              borderRadius: "50%",
            }}
          >
            <Box
              component="span"
              sx={{ position: "absolute", left: 22, top: -4, color: "#FFD54F", fontSize: 12, whiteSpace: "nowrap" }}
            >
              {m.label}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}
