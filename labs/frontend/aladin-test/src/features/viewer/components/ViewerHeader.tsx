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
              sx={{ fontSize: { xs: 34, sm: 40 }, fontWeight: 400, lineHeight: 1, letterSpacing: "0.03em" }}
            >
              ÉTER
            </Typography>
            <Box sx={{ lineHeight: 1.25 }}>
              <Typography
                sx={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.14em", color: "rgba(255,255,255,0.55)" }}
              >
                Visor espectral
              </Typography>
              <Typography sx={{ fontSize: 14, color: "rgba(255,255,255,0.8)" }}>SPHEREx</Typography>
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
              backgroundColor: "rgba(0,0,0,0.35)",
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
            backgroundColor: "rgba(0,0,0,0.35)",
            backdropFilter: "blur(8px)",
            "&:hover": { backgroundColor: "rgba(255,255,255,0.1)" },
          }}
        >
          <Box component="span" sx={{ display: "grid", gap: "6px" }}>
            {[0, 1, 2].map((n) => (
              <Box key={n} component="span" sx={{ display: "block", width: 20, height: "1px", backgroundColor: "#fff" }} />
            ))}
          </Box>
        </IconButton>
      </Box>  
    );
}