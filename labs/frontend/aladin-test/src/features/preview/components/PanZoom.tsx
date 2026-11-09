"use client";

import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Add from "@mui/icons-material/Add";
import Remove from "@mui/icons-material/Remove";
import RestartAlt from "@mui/icons-material/RestartAlt";

type View = { scale: number; x: number; y: number };

const MIN_SCALE = 1;
const MAX_SCALE = 8;
const START: View = { scale: 1, x: 0, y: 0 };

/** Mantiene la imagen cubriendo la pantalla: no deja ver los bordes vacíos. */
const clamp = (v: View, w: number, h: number): View => ({
  scale: v.scale,
  x: Math.min(0, Math.max(w - w * v.scale, v.x)),
  y: Math.min(0, Math.max(h - h * v.scale, v.y)),
});

/** Cambia el zoom multiplicando por `factor`, manteniendo fijo el punto (cx, cy). */
const zoomView = (v: View, factor: number, cx: number, cy: number, w: number, h: number): View => {
  const s = Math.min(MAX_SCALE, Math.max(MIN_SCALE, v.scale * factor));
  const k = s / v.scale;
  return clamp({ scale: s, x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k }, w, h);
};

const buttonSx = {
  color: "#fff",
  border: "1px solid rgba(255,255,255,0.25)",
  backgroundColor: "rgba(0,0,0,0.45)",
  backdropFilter: "blur(6px)",
  "&:hover": { backgroundColor: "rgba(255,255,255,0.18)" },
};

/**
 * Hace que todo lo que lleva dentro (canvas + marcadores) se pueda arrastrar y ampliar.
 * Rueda o dos dedos en el touchpad = zoom hacia el cursor. Arrastrar = mover.
 * Botones + / − / reiniciar a un costado. Doble clic = volver al inicio.
 */
export default function PanZoom({ children }: { children: ReactNode }) {
  const [view, setView] = useState<View>(START);
  const box = useRef<HTMLDivElement>(null);
  const drag = useRef<{ px: number; py: number; x: number; y: number } | null>(null);

  // El listener va "a mano" para poder bloquear el scroll de la página con preventDefault.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      // deltaMode 1 = líneas (algunos navegadores): se convierte a píxeles.
      const dy = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
      // El pellizco del touchpad llega con ctrlKey y deltas pequeños: se amplifica.
      const speed = e.ctrlKey ? 0.012 : 0.003;
      setView((v) => zoomView(v, Math.exp(-dy * speed), e.clientX - r.left, e.clientY - r.top, r.width, r.height));
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  const zoomFromCenter = (factor: number) => {
    const el = box.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    setView((v) => zoomView(v, factor, r.width / 2, r.height / 2, r.width, r.height));
  };

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { px: e.clientX, py: e.clientY, x: view.x, y: view.y };
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    const el = box.current;
    if (!d || !el) return;
    const r = el.getBoundingClientRect();
    setView((v) =>
      clamp({ scale: v.scale, x: d.x + e.clientX - d.px, y: d.y + e.clientY - d.py }, r.width, r.height),
    );
  };

  const endDrag = () => {
    drag.current = null;
  };

  return (
    <Box
      ref={box}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onDoubleClick={() => setView(START)}
      sx={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        touchAction: "none",
        cursor: "grab",
        "&:active": { cursor: "grabbing" },
      }}
    >
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          transformOrigin: "0 0",
          transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
        }}
      >
        {children}
      </Box>

      {/* Botones de zoom. Detienen el clic para que no cuente como arrastre de la imagen. */}
      <Box
        onPointerDown={(e) => e.stopPropagation()}
        onDoubleClick={(e) => e.stopPropagation()}
        sx={{
          position: "absolute",
          left: 16,
          top: "50%",
          transform: "translateY(-50%)",
          display: "flex",
          flexDirection: "column",
          gap: 1,
          cursor: "default",
        }}
      >
        <IconButton aria-label="Acercar" onClick={() => zoomFromCenter(1.5)} sx={buttonSx}>
          <Add />
        </IconButton>
        <IconButton aria-label="Alejar" onClick={() => zoomFromCenter(1 / 1.5)} sx={buttonSx}>
          <Remove />
        </IconButton>
        <IconButton aria-label="Reiniciar vista" onClick={() => setView(START)} sx={buttonSx}>
          <RestartAlt />
        </IconButton>
      </Box>
    </Box>
  );
}