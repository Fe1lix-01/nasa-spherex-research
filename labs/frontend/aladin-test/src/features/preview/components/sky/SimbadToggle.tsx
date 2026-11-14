"use client";

import Box from "@mui/material/Box";
import { eter, selectedRing } from "@/theme/theme";

const SIZE = 40;
const BUBBLE = "rgb(14,20,30)"; // mismo color en el globo y en su flecha, para que no se noten dos tonos

/**
 * Interruptor de la capa de objetos de SIMBAD. Encendido lleva el mismo borde de luz giratorio que el
 * botón "Subir imagen" (selectedRing); apagado se queda como un círculo de vidrio discreto.
 * `loading` hace latir el icono mientras la capa consulta SIMBAD.
 *
 * El globo de texto es CSS puro: aparece con :hover o :focus-visible del botón y se queda oculto el resto
 * del tiempo. El contenedor no recibe clics (solo el botón), así no estorba al mapa.
 */
export default function SimbadToggle({
  on,
  loading,
  onToggle,
}: {
  on: boolean;
  loading: boolean;
  onToggle: () => void;
}) {
  return (
    <Box
      sx={{
        position: "absolute",
        left: 84, // junto a los botones de zoom de Aladin; ajusta este número si se encima
        bottom: 12,
        display: "flex",
        pointerEvents: "none",
        // El globo es el hermano que sigue al botón. La espera de 350 ms solo aplica al aparecer.
        "& button:hover + [role=tooltip], & button:focus-visible + [role=tooltip]": {
          opacity: 1,
          transform: "translate(-50%, 0)",
          transitionDelay: "350ms",
        },
      }}
    >
      <Box
        component="button"
        type="button"
        aria-pressed={on}
        aria-label="Objetos estelares" // fijo: el estado lo anuncia aria-pressed
        onClick={onToggle}
        sx={{
          all: "unset",
          // Solo encendido lleva el aro (selectedRing fija position: relative, que es lo que necesitamos).
          ...(on ? selectedRing("0px", "50%") : { position: "relative" }),
          width: SIZE,
          height: SIZE,
          boxSizing: "border-box",
          borderRadius: "50%",
          display: "grid",
          placeItems: "center",
          cursor: "pointer",
          pointerEvents: "auto", // el contenedor no recibe clics; el botón sí
          color: on ? "#fff" : eter.textMuted,
          background: on ? "rgba(12,18,28,0.72)" : "rgba(12,18,28,0.55)",
          backdropFilter: "blur(14px) saturate(140%)",
          WebkitBackdropFilter: "blur(14px) saturate(140%)",
          border: on ? "1px solid transparent" : `1px solid ${eter.lineStrong}`, // encendido: el borde lo dibuja el aro
          boxShadow: on
            ? "inset 0 1px 0 rgba(255,255,255,0.08), 0 0 18px rgba(255,255,255,0.14)"
            : "inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 24px rgba(0,0,0,0.35)",
          transition: "color 160ms ease, background 160ms ease, border-color 160ms ease, transform 120ms ease",
          "&:hover": {
            color: "#fff",
            borderColor: on ? "transparent" : eter.lineHover,
            background: "rgba(24,32,46,0.78)",
          },
          "&:active": { transform: "scale(0.94)" },
          "&:focus-visible": { outline: `2px solid ${eter.focusRing}`, outlineOffset: 3 },
          "& svg": { animation: loading ? "simbadTogglePulse 1.2s ease-in-out infinite" : "none" },
          "@keyframes simbadTogglePulse": { "0%,100%": { opacity: 0.45 }, "50%": { opacity: 1 } },
          "@media (prefers-reduced-motion: reduce)": { "& svg": { animation: "none" }, transition: "none" },
        }}
      >
        {/* Tres anillos de distinto tamaño: las mismas marcas que se dibujan sobre las estrellas. */}
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <circle cx="6.5" cy="12.5" r="3.5" />
          <circle cx="14" cy="6" r="2.5" />
          <circle cx="14.5" cy="14.5" r="2" />
        </svg>
      </Box>

      {/* Globo de texto con flecha hacia el botón */}
      <Box
        role="tooltip"
        sx={{
          position: "absolute",
          bottom: "calc(100% + 10px)",
          left: "50%",
          transform: "translate(-50%, 4px)", // arranca un poco abajo y sube al aparecer
          opacity: 0,
          transition: "opacity 120ms ease, transform 120ms ease",
          px: 1.5,
          py: 0.75,
          borderRadius: "10px",
          fontSize: 12.5,
          letterSpacing: "0.02em",
          whiteSpace: "nowrap",
          color: "rgba(255,255,255,0.92)",
          background: BUBBLE,
          border: `1px solid ${eter.lineStrong}`,
          boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 24px rgba(0,0,0,0.35)",
          pointerEvents: "none",
          "&::after": {
            content: '""',
            position: "absolute",
            left: "50%",
            bottom: -5,
            width: 8,
            height: 8,
            background: BUBBLE,
            borderRight: `1px solid ${eter.lineStrong}`,
            borderBottom: `1px solid ${eter.lineStrong}`,
            transform: "translateX(-50%) rotate(45deg)",
          },
          "@media (prefers-reduced-motion: reduce)": { transition: "none" },
        }}
      >
        {on ? "Ocultar objetos estelares" : "Mostrar objetos estelares"}
      </Box>
    </Box>
  );
}