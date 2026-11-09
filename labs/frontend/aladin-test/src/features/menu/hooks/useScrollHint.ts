"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Detecta si queda contenido por debajo en un contenedor con scroll
 * y vuelve arriba cuando cambia resetKey.
 */
export function useScrollHint(resetKey: unknown) {
  // Guarda las referencias de los elementos del Drawer.
  const [bodyEl, setBodyEl] = useState<HTMLDivElement | null>(null);
  const [innerEl, setInnerEl] = useState<HTMLDivElement | null>(null);

  // Indica si todavía hay contenido por debajo.
  const [more, setMore] = useState(false);

  // Comprueba si el contenedor tiene contenido pendiente por desplazar.
  const check = useCallback(() => {
    if (!bodyEl) return;

    setMore(
      bodyEl.scrollHeight - bodyEl.scrollTop - bodyEl.clientHeight > 12
    );
  }, [bodyEl]);

  // Al cambiar de sección, vuelve al inicio del contenedor.
  useEffect(() => {
    bodyEl?.scrollTo({ top: 0 });
  }, [resetKey, bodyEl]);

  // Observa cambios en las dimensiones del contenedor y su contenido.
  useEffect(() => {
    if (!bodyEl || !innerEl || typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver(check);

    ro.observe(bodyEl);
    ro.observe(innerEl);

    return () => ro.disconnect();
  }, [bodyEl, innerEl, check]);

  // Desplaza el contenedor hacia abajo suavemente.
  const scrollDown = useCallback(() => {
    bodyEl?.scrollBy({ top: 240, behavior: "smooth" });
  }, [bodyEl]);

  // Expone las referencias, el estado y las acciones del scroll.
  return { setBodyEl, setInnerEl, more, check, scrollDown };
}