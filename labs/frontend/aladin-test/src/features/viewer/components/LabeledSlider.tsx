"use client";

import { useEffect, useId, useRef } from "react";
import Box from "@mui/material/Box";
import Slider from "@mui/material/Slider";
import Typography from "@mui/material/Typography";
import { RING_ANGLE } from "@/theme/theme";
import { glowSliderParts } from "@/theme/sliderStyles";

type Props = {
  label: string;
  value: number;
  min: number;
  max: number;
  disabled?: boolean;
  onChange: (value: number) => void;
};

// Velocidad máxima del giro del aro de la perilla y qué tan rápido acelera o frena.
const SPIN_DEG_PER_SEC = 150;
const EASE_RATE = 6;
// Tras soltar, el aro sigue girando un momento mientras frena (también cubre el teclado).
const LINGER_MS = 400;

/** Slider con etiqueta, valor en ámbar y límites mínimo y máximo. */
export default function LabeledSlider({ label, value, min, max, disabled, onChange }: Props) {
  // useId liga la etiqueta con el slider para que los lectores de pantalla lo anuncien.
  const labelId = useId();

  const rootRef = useRef<HTMLSpanElement>(null);
  // Estado del giro. Vive en un ref porque cambia en cada fotograma y no debe redibujar React.
  const spin = useRef({ angle: RING_ANGLE, speed: 0, dir: 1, holding: false, until: 0 });
  // Arranca el bucle de animación si estaba detenido (lo asigna el efecto de abajo).
  const kick = useRef<() => void>(() => {});

  useEffect(() => {
    // Quien prefiere menos movimiento ve la perilla con el aro quieto.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let raf = 0;
    let last = 0;

    const frame = (now: number) => {
      const s = spin.current;
      const dt = Math.min((now - last) / 1000, 0.05); // tope: evita saltos si la pestaña estuvo en segundo plano
      last = now;

      const active = s.holding || now < s.until;
      const target = active ? s.dir * SPIN_DEG_PER_SEC : 0;
      // Acercamiento exponencial a la velocidad objetivo: arranca y frena sin tirones.
      s.speed += (target - s.speed) * (1 - Math.exp(-dt * EASE_RATE));
      s.angle = (s.angle + s.speed * dt) % 360;
      rootRef.current?.style.setProperty("--ring-angle", `${s.angle}deg`);

      // El bucle se detiene solo cuando el aro ya frenó del todo.
      raf = active || Math.abs(s.speed) > 0.5 ? requestAnimationFrame(frame) : 0;
    };

    kick.current = () => {
      if (raf) return;
      last = performance.now();
      raf = requestAnimationFrame(frame);
    };

    return () => cancelAnimationFrame(raf);
  }, []);

  // 0 en el mínimo, 1 en el máximo: sirve igual para 0–100 y para 10–300.
  const p = max > min ? Math.min(Math.max((value - min) / (max - min), 0), 1) : 0;

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <Typography id={labelId} sx={{ fontSize: 15, color: "rgba(255,255,255,0.9)" }}>
          {label}
        </Typography>
        <Typography sx={{ fontSize: 14, fontWeight: 500, color: "#fff" }}>{value} %</Typography> 
      </Box>

      <Slider
        ref={rootRef}
        aria-labelledby={labelId}
        getAriaValueText={(v) => `${v} %`}
        value={value}
        min={min}
        max={max}
        disabled={disabled}
        valueLabelDisplay="off"
        // MUI entrega number | number[]; aquí siempre es un solo valor.
        onChange={(_, v) => {
          const next = Array.isArray(v) ? v[0] : v;
          const s = spin.current;
          // Derecha = sentido horario (+1), izquierda = antihorario (-1).
          if (next !== value) s.dir = next > value ? 1 : -1;
          s.holding = true;
          kick.current();
          onChange(next);
        }}
        onChangeCommitted={() => {
          const s = spin.current;
          s.holding = false;
          s.until = performance.now() + LINGER_MS;
          kick.current();
        }}
                sx={{
          height: 2,
          mt: 0.5,
          // Sin animación CSS: el giro del aro lo mueve el script de arriba, según la dirección.
          ...glowSliderParts(p, false),
          "&.Mui-disabled": { opacity: 0.35 },
        }}
      />

      <Box sx={{ display: "flex", justifyContent: "space-between", mt: -0.5 }}>
        <Typography variant="caption" sx={{ color: "text.disabled" }}>
          {min} %
        </Typography>
        <Typography variant="caption" sx={{ color: "text.disabled" }}>
          {max} %
        </Typography>
      </Box>
    </Box>
  );
}