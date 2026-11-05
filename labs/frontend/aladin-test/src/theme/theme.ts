import { createTheme } from "@mui/material/styles";

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
} as const;

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