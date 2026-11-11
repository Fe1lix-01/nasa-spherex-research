import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import FiberManualRecord from "@mui/icons-material/FiberManualRecord";
import { eter } from "@/theme/theme";

type Props = {
  /** Texto del chip, por ejemplo "Visible · 0.38–0.75 µm". */
  filterLabel: string;
  menuOpen: boolean;
  onOpenMenu: () => void;
};

export default function ViewerHeader({ filterLabel, menuOpen, onOpenMenu }: Props) {
  
  // Movimiento de cada línea al abrir el menú: la de arriba y la de abajo giran
// hacia el centro formando una X, y la del medio desaparece.
const OPEN_LINE_STYLE = [
  { transform: "translateY(6px) rotate(45deg)" },
  { opacity: 0 },
  { transform: "translateY(-6px) rotate(-45deg)" },
];
  
  return (
      <Box
        component="header"
        sx={{
          pointerEvents: "none",
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 2,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          p: { xs: 2, sm: 3.5 },
        }}
      >
        <Box sx={{ pointerEvents: "auto" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Typography
  component="h1"
  sx={{ 
    fontSize: { xs: 26, sm: 34, md: 40 }, // Se ajusta según la pantalla: móvil pequeño (xs), tablet (sm) y PC (md)
    fontWeight: 400, 
    lineHeight: 1.1, 
    letterSpacing: "0.03em",
    wordBreak: "break-word" // Evita desbordamientos si la pantalla es extremadamente pequeña
  }}
>
  Project Morley
</Typography>
<Box sx={{ lineHeight: 1.25, mt: 0.5 }}>
  <Typography
    sx={{ fontSize: { xs: 9, sm: 10 }, textTransform: "uppercase", letterSpacing: "0.14em", color: eter.textFaint }}
  >
    Visor espectral
  </Typography>
  <Typography sx={{ fontSize: { xs: 12, sm: 14 }, color: "rgba(255,255,255,0.8)" }}>SPHEREx</Typography>
</Box>
</Box>
          <Chip
            variant="outlined"
            icon={<FiberManualRecord />}
            label={filterLabel}
            sx={{
              mt: 1.5,
              height: 34,
              color: "#fff",
              borderColor: eter.lineStrong,
              backgroundColor: eter.glass,
              backdropFilter: "blur(8px)",
              "& .MuiChip-icon": { fontSize: 8, ml: 1.5, mr: -0.5, color: eter.accent },
              "& .MuiChip-label": { fontSize: 14 },
            }}
          />
        </Box>

        {/* Botón de tres líneas */}
        <IconButton
          onClick={onOpenMenu}
          aria-label="Abrir menú"
          aria-expanded={menuOpen}
          sx={{
            pointerEvents: "auto",
            width: { xs: 48, sm: 56 },
            height: { xs: 48, sm: 56 },
            borderRadius: "16px",
            border: `1px solid ${eter.lineStrong}`,
            backgroundColor: eter.glass,
            backdropFilter: "blur(8px)",
            "&:hover": { backgroundColor: "rgba(255,255,255,0.1)" },
          }}
        >
                    {/* Las tres líneas se superponen para poder girarlas hacia una X */}
          <Box component="span" sx={{ position: "relative", width: 20, height: 13 }}>
            {[0, 1, 2].map((n) => (
              <Box
                key={n}
                component="span"
                sx={{
                  position: "absolute",
                  left: 0,
                  top: n * 6,
                  width: 20,
                  height: "1px",
                  backgroundColor: "#fff",
                  transition: "transform 350ms ease, opacity 200ms ease",
                  // Si el usuario pide menos movimiento, el cambio es instantáneo.
                  "@media (prefers-reduced-motion: reduce)": { transition: "none" },
                  ...(menuOpen ? OPEN_LINE_STYLE[n] : null),
                }}
              />
            ))}
          </Box>
        </IconButton>
      </Box>  
    );
}