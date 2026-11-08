"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./AnimatedButton.css";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

/**
 * Botón con un borde que recorre un destello sutil. Todo es CSS: no usa WebGL,
 * así que funciona igual en cualquier navegador. El movimiento se apaga si el
 * usuario pide menos animaciones (ver AnimatedButton.css).
 */
export default function AnimatedButton({ children, className = "", type = "button", ...rest }: Props) {
  return (
    <button type={type} className={`animated-button ${className}`.trim()} {...rest}>
      <span className="animated-button__label">{children}</span>
    </button>
  );
}