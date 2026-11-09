"use client";

import Box from "@mui/material/Box";
import type { Frame } from "@/contracts";
import { skyToImage } from "../projection";
import type { SkyPoint } from "../trajectory";

type Props = {
  frame: Frame;
  /** Posiciones medidas del objeto, una por época en la que se detectó. */
  points: (SkyPoint & { index: number })[];
  /** Instante actual de la animación (0 = primera época). */
  t: number;
};

/**
 * Rastro del objeto: línea punteada por donde se mueve y un punto por cada época.
 * Los puntos se rellenan cuando la animación ya pasó por esa época.
 */
export default function TrailLayer({ frame, points, t }: Props) {
  const placed = points.flatMap((p) => {
    const pos = skyToImage(p.ra, p.dec, frame);
    return pos ? [{ ...p, ...pos }] : [];
  });
  if (placed.length === 0) return null;

  const line = placed.map((p) => `${p.x * 100},${p.y * 100}`).join(" ");

  return (
    <Box sx={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {placed.length > 1 && (
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ position: "absolute", inset: 0 }}
        >
          <polyline
            points={line}
            fill="none"
            stroke="rgba(255,213,79,0.6)"
            strokeWidth={1.5}
            strokeDasharray="5 5"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
      )}
      {placed.map((p) => (
        <Box
          key={p.index}
          sx={{
            position: "absolute",
            left: `${p.x * 100}%`,
            top: `${p.y * 100}%`,
            width: 8,
            height: 8,
            transform: "translate(-50%, -50%)",
            borderRadius: "50%",
            border: "1.5px solid #FFD54F",
            bgcolor: t >= p.index - 0.001 ? "#FFD54F" : "transparent",
          }}
        />
      ))}
    </Box>
  );
}
