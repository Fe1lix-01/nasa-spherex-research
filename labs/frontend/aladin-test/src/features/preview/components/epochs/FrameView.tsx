"use client";

import Box from "@mui/material/Box";
import type { Frame } from "@/contracts";
import { skyToImage } from "@/features/preview/model/projection";

export type Marker = { id: string; label: string; ra: number; dec: number };

type Props = { frame: Frame; markers: Marker[] };

/** Muestra la imagen de una época y encima los marcadores de los objetos. */
export default function FrameView({ frame, markers }: Props) {
  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        maxWidth: 720,
        aspectRatio: "1 / 1",
        mx: "auto",
        bgcolor: "#000",
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      {/* "fill" para que el mapeo de porcentajes coincida exactamente con la imagen */}
      <Box
        component="img"
        src={frame.imageUrl}
        alt={`Imagen de la época ${frame.epochId}`}
        sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "fill" }}
      />
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
              pointerEvents: "none",
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
