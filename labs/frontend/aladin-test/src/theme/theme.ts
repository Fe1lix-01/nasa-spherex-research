import { createTheme } from "@mui/material/styles";

/** Colores del diseño de Figma. Úsalos en `sx` cuando el tema no los cubra. */
export const eter = {
  accent: "#ffd24c", // ámbar: filtro activo, valores, títulos abiertos
  ink: "#05080d", // fondo base
  panel: "#0a0f16", // panel inferior y menú
  card: "#10151c", // tarjetas
  line: "rgba(255,255,255,0.10)", // separadores
  lineStrong: "rgba(255,255,255,0.15)", // bordes de botones y tarjetas
} as const;

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: eter.accent, contrastText: "#000000" },
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
