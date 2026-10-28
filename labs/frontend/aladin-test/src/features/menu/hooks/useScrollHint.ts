"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Detecta si queda contenido por debajo en un contenedor con scroll (para mostrar la
 * flecha ↓) y vuelve arriba cuando cambia `resetKey`.
 */
export function useScrollHint(resetKey: unknown) {
  // Referencias como estado: el contenido del Drawer se monta un instante después de abrir.
  const [bodyEl, setBodyEl] = useState<HTMLDivElement | null>(null);
  const [innerEl, setInnerEl] = useState<HTMLDivElement | null>(null);
  const [more, setMore] = useState(false);

  const check = useCallback(() => {
    if (!bodyEl) return;
    setMore(bodyEl.scrollHeight - bodyEl.scrollTop - bodyEl.clientHeight > 12);
  }, [bodyEl]);

  // Al cambiar de sección vuelve arriba.
  useEffect(() => {
    bodyEl?.scrollTo({ top: 0 });
  }, [resetKey, bodyEl]);

  // Recalcula la flecha cuando cambia el alto del contenido (acordeón animándose, resize).
  useEffect(() => {
    if (!bodyEl || !innerEl || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(check);
    ro.observe(bodyEl);
    ro.observe(innerEl);
    check();
    return () => ro.disconnect();
  }, [bodyEl, innerEl, check]);

  const scrollDown = useCallback(() => {
    bodyEl?.scrollBy({ top: 240, behavior: "smooth" });
  }, [bodyEl]);

  return { setBodyEl, setInnerEl, more, check, scrollDown };
}