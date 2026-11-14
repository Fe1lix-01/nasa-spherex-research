"use client";

import { useEffect } from "react";
import "./glow-buttons.css";

const SPIN_DEG_PER_SEC = 60; // una vuelta cada 6 segundos, igual que AnimatedButton
const SELECTOR = ".MuiButton-root, .MuiIconButton-root, .MuiToggleButton-root";

/**
 * Un solo reloj que gira el destello de todos los botones de MUI. Un único ciclo de
 * animación sirve para cualquier cantidad de botones. Respeta "reducir movimiento".
 */
export default function GlowClock() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let last = 0;
    let angle = 0;

    const paint = () => {
      document.querySelectorAll<HTMLElement>(SELECTOR).forEach((el) => {
        el.style.setProperty("--glow-angle", `${angle}deg`);
      });
    };

    const frame = (now: number) => {
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 0;
      last = now;
      angle = (angle + SPIN_DEG_PER_SEC * dt) % 360;
      paint();
      raf = requestAnimationFrame(frame);
    };

    if (reduce) {
      paint(); // quieto
    } else {
      raf = requestAnimationFrame(frame);
    }
    return () => cancelAnimationFrame(raf);
  }, []);

  return null;
}
