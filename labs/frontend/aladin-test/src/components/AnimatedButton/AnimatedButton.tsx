"use client";

import { useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import "./AnimatedButton.css";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

const SPIN_DEG_PER_SEC = 60; // una vuelta cada 6 segundos
const FOLLOW_RATE = 6; // qué tan ágil sigue el destello al cursor (mayor = más rápido)

// Diferencia más corta entre dos ángulos, en grados (de -180 a 180).
const shortestDelta = (from: number, to: number) => ((((to - from) % 360) + 540) % 360) - 180;

/**
 * Botón con un destello que recorre el borde. Lo calcula JavaScript y lo suaviza
 * en cada cuadro: el giro nunca se reinicia, y al pasar el cursor el destello se
 * acerca a él poco a poco. No usa WebGL.
 */
export default function AnimatedButton({
  children,
  className = "",
  type = "button",
  onPointerEnter,
  onPointerMove,
  onPointerLeave,
  ...rest
}: Props) {
  const ref = useRef<HTMLButtonElement>(null);
  // Estado que no provoca renders: cambiarlo cada cuadro no debe redibujar React.
  const motion = useRef({ shown: 0, base: 0, cursor: 0, hovering: false, last: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const m = motion.current;
    let raf = 0;

    const frame = (now: number) => {
      const dt = m.last ? Math.min(0.05, (now - m.last) / 1000) : 0;
      m.last = now;
      if (!reduce) m.base += SPIN_DEG_PER_SEC * dt;
      // Con el cursor encima, el destello apunta a él; si no, sigue girando.
      const target = m.hovering ? m.cursor : m.base;
      m.shown += shortestDelta(m.shown, target) * (1 - Math.exp(-dt * FOLLOW_RATE));
      el.style.setProperty("--ab-angle", `${m.shown}deg`);
      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  const handlePointerEnter = (e: React.PointerEvent<HTMLButtonElement>) => {
    motion.current.hovering = true;
    onPointerEnter?.(e);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const el = ref.current;
    if (el) {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      // 0° hacia arriba, ángulos crecen en sentido horario (y crece hacia abajo en pantalla).
      motion.current.cursor = (Math.atan2(x, -y) * 180) / Math.PI;
    }
    onPointerMove?.(e);
  };

  const handlePointerLeave = (e: React.PointerEvent<HTMLButtonElement>) => {
    motion.current.hovering = false;
    onPointerLeave?.(e);
  };

  return (
    <button
      ref={ref}
      type={type}
      className={`animated-button ${className}`.trim()}
      onPointerEnter={handlePointerEnter}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      {...rest}
    >
      <span className="animated-button__label">{children}</span>
    </button>
  );
}