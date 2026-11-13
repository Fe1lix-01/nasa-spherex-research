"use client";

import { useEffect, useRef } from "react";
import Box from "@mui/material/Box";
import { selectedRing } from "@/theme/theme";
import type { SimbadObject } from "../../model/simbad";
import type { SimbadAladinView } from "./useSimbadLayer";

/** Diámetro del aro, un poco mayor que el círculo blanco que dibuja Aladin. */
const SIZE = 28;

/**
 * Aro de luz sobre el objeto elegido: el mismo del botón "Subir imagen" (selectedRing), girando.
 *
 * Aladin dibuja sus marcas en un canvas y ahí no cabe un borde animado con CSS, así que el aro es
 * un elemento HTML encima del mapa. Para que siga al objeto al mover o hacer zoom, se recalcula su
 * posición en cada cuadro con world2pix y se escribe directo en el DOM (sin pasar por el estado de
 * React, que repintaría el componente 60 veces por segundo).
 */
export default function SimbadSelectedRing({
  view,
  object,
}: {
  view: SimbadAladinView | null;
  object: SimbadObject | null;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!view || !object) return;
    let raf = 0;

    const follow = () => {
      const el = ref.current;
      if (el) {
        let p: number[] | null | undefined = null;
        try {
          p = view.world2pix(object.ra, object.dec);
        } catch {
          /* el mapa aún no está listo: se reintenta en el siguiente cuadro */
        }
        if (p && Number.isFinite(p[0]) && Number.isFinite(p[1])) {
          el.style.transform = `translate(${p[0]}px, ${p[1]}px)`;
          el.style.visibility = "visible";
        } else {
          el.style.visibility = "hidden"; // el objeto quedó detrás de la proyección
        }
      }
      raf = requestAnimationFrame(follow);
    };

    raf = requestAnimationFrame(follow);
    return () => cancelAnimationFrame(raf);
  }, [view, object]);

  if (!object) return null;

  return (
    // Contenedor sin tamaño: su esquina es el punto exacto del objeto; el aro se centra sobre él.
    <Box ref={ref} sx={{ position: "absolute", left: 0, top: 0, width: 0, height: 0, visibility: "hidden" }}>
      <Box
        key={object.oid} // al elegir otro objeto, la entrada se anima de nuevo
        sx={{
          ...selectedRing("0px", "50%"),
          width: SIZE,
          height: SIZE,
          ml: `${-SIZE / 2}px`,
          mt: `${-SIZE / 2}px`,
          borderRadius: "50%",
          boxShadow: "0 0 18px rgba(255,255,255,0.18)",
          animation: "simbadRingIn 200ms ease-out",
          "@keyframes simbadRingIn": {
            from: { opacity: 0, transform: "scale(0.6)" },
            to: { opacity: 1, transform: "scale(1)" },
          },
          "@media (prefers-reduced-motion: reduce)": { animation: "none" },
        }}
      />
    </Box>
  );
}