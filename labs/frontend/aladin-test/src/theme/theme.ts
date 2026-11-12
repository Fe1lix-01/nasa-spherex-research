import { createTheme, keyframes } from "@mui/material/styles";

/** Colores del diseño de Figma. Úsalos en `sx` cuando el tema no los cubra. */
export const eter = {
  accent: "#ffd24c", // ámbar: filtro activo, valores, títulos abiertos
  ink: "#05080d", // fondo base
  panel: "#0a0f16", // panel inferior y menú
  card: "#10151c", // tarjetas
  line: "rgba(255,255,255,0.10)", // separadores
  lineStrong: "rgba(255,255,255,0.15)", // bordes de botones y tarjetas

  // --- Texto sobre fondo oscuro (blanco con distinta opacidad) ---
  onAccent: "#000", // texto encima del ámbar (chip activo)
  textMuted: "rgba(255,255,255,0.6)", // botones discretos y chips inactivos
  textFaint: "rgba(255,255,255,0.55)", // etiquetas pequeñas (eyebrow)

  // --- Superficies "de vidrio" sobre la imagen ---
  glass: "rgba(0,0,0,0.35)", // chip y botón del encabezado
  panelGlass: "rgba(10,15,22,0.9)", // panel de controles (eter.panel con transparencia)

  // --- Interacción ---
  lineHover: "rgba(255,255,255,0.3)", // borde al pasar el mouse
  hoverFill: "rgba(255,255,255,0.05)", // relleno al pasar el mouse

  // --- Slider ---
  rail: "rgba(255,255,255,0.16)", // riel
  accentGlow: "rgba(255,210,76,0.18)", // resplandor del control (ámbar con transparencia)
  accentGlowStrong: "rgba(255,210,76,0.28)", // resplandor al pasar el mouse o enfocar

  // --- Foco y errores ---
  focusRing: "rgba(255,255,255,0.6)", // anillo de foco visible con el teclado
  danger: "#ff9aa8", // mensajes de error
} as const;

/**
 * Superficie de vidrio para los paneles grandes (reproductor de épocas y panel de controles).
 * La opacidad de 0.55 deja ver la imagen de fondo, y el desenfoque evita que compita con
 * el texto. Para más o menos transparencia, cambia solo ese 0.55 (rango útil: 0.45 a 0.7).
 */
export const glassPanel = {
  backgroundColor: "rgba(12,18,28,0.45)",
  backdropFilter: "blur(20px) saturate(140%)",
  WebkitBackdropFilter: "blur(20px) saturate(140%)", // Safari
  border: `1px solid ${eter.lineStrong}`,
  // Línea de luz arriba (borde de cristal) y sombra suave para separarlo del fondo.
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.08), 0 20px 40px -16px rgba(0,0,0,0.5)",
} as const;

/**
 * Borde "de luz" para el elemento seleccionado: el mismo degradado del botón Subir imagen
 * (AnimatedButton), pero quieto. Un arco blanco que se desvanece a gris sobre un borde de 1 px.
 * `inset` y `radius` ajustan dónde se dibuja el aro según el componente que lo use.
 */
export const RING_ANGLE = 315; // grados donde empieza el destello (315° = esquina superior izquierda)
const RING_BASE = "rgba(255,255,255,0.35)"; // el borde completo, visible en todo el contorno
const RING_LIGHT = "#ffffff"; // el destello

// Gira el destello una vuelta completa. Se anima la variable --ring-angle (registrada con
// @property más abajo): sin registrarla, el navegador no sabe interpolar el ángulo y saltaría.
const ringSpin = keyframes`
  from { --ring-angle: ${RING_ANGLE}deg; }
  to { --ring-angle: ${RING_ANGLE + 360}deg; }
`;

/**
 * Borde "de luz" para el elemento seleccionado: el mismo degradado del botón Subir imagen,
 * girando sin parar. No reacciona al cursor. `spin = false` lo deja quieto (p. ej. en pausa).
 * `inset` y `radius` ajustan dónde se dibuja el aro según el componente que lo use.
 */
export const selectedRing = (inset: string, radius: string, spin = true) =>
  ({
    position: "relative",
    isolation: "isolate",
    "&::before": {
      content: '""',
      position: "absolute",
      inset,
      zIndex: -1, // detrás del texto, encima del fondo del propio botón
      borderRadius: radius,
      padding: "1px", // grosor del aro
      background: `conic-gradient(from var(--ring-angle, ${RING_ANGLE}deg), ${RING_LIGHT} 0deg, ${RING_BASE} 110deg, ${RING_BASE} 250deg, ${RING_LIGHT} 360deg)`,
      // Deja visible solo el borde: se recorta el interior con la máscara.
      WebkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
      mask: "linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0)",
      pointerEvents: "none",
      animation: spin ? `${ringSpin} 4s linear infinite` : "none",
      // Quien prefiere menos movimiento ve el aro quieto.
      "@media (prefers-reduced-motion: reduce)": { animation: "none" },
    },
  }) as const;

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: eter.accent, contrastText: eter.onAccent },
    background: { default: eter.ink, paper: eter.panel },
    text: {
      primary: "#ffffff",
      secondary: "rgba(255,255,255,0.65)",
      disabled: "rgba(255,255,255,0.45)",
    },
    divider: eter.line,
  },
  shape: { borderRadius: 12 },
  typography: {
    // --font-inter la define next/font en app/layout.tsx
    fontFamily:
      'var(--font-inter), "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    button: { textTransform: "none", fontWeight: 400 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
                // Permite animar el ángulo del aro de luz (ver ringSpin).
        "@property --ring-angle": {
          syntax: '"<angle>"',
          inherits: true, // el slider mueve el ángulo en su raíz y la perilla lo hereda
          initialValue: `${RING_ANGLE}deg`,
        },
        html: { height: "100%" },
        body: {
          height: "100dvh",
          overflow: "hidden",
          backgroundColor: eter.ink,
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
    },
  },
});

export default theme;