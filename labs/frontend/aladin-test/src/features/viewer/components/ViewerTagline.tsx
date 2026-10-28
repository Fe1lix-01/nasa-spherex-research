import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

export default function ViewerTagline({ sourceLabel }: { sourceLabel: string }) {
  return (
    <Box
      sx={{
        position: { xs: "static", lg: "absolute" },
        bottom: { lg: 248 },
        left: { lg: 28 },
      }}
    >
      <Typography
        sx={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.14em", color: "rgba(255,255,255,0.55)" }}
      >
        Exploración infrarroja
      </Typography>
      <Typography
        component="h2"
        sx={{
          mt: 0.5,
          fontSize: { xs: 24, lg: 28 },
          fontWeight: 300,
          textShadow: "0 1px 14px rgba(0,0,0,0.6)",
        }}
      >
        Entre el polvo y la luz.
      </Typography>
      <Typography sx={{ mt: 0.5, fontSize: 12, color: "rgba(255,255,255,0.5)" }}>
        {sourceLabel} · Visualización ilustrativa
      </Typography>
    </Box>
  );
}