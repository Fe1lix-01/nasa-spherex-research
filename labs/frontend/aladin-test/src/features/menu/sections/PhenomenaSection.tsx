import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { PHENOMENA_INTRO } from "@/features/menu/content";
import { PHENOMENA } from "@/features/phenomena/data";
import PhenomenonArt from "@/features/phenomena/PhenomenonArt";
import { eter } from "@/theme/theme";

export default function PhenomenaContent() {
  return (
    <Box>
      <Typography sx={{ fontSize: 15, lineHeight: 1.7, color: "text.secondary" }}>{PHENOMENA_INTRO}</Typography>
      <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, mt: 2, display: "grid", gap: 1.5 }}>
        {PHENOMENA.map((ph) => (
          <Box
            component="li"
            key={ph.id}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 2,
              p: 1.5,
              borderRadius: "16px",
              border: "1px solid rgba(255,255,255,0.12)",
              backgroundColor: eter.card,
            }}
          >
            {/* Si la foto no carga, Avatar muestra la ilustración SVG de respaldo (children). */}
            <Avatar
              variant="rounded"
              src={ph.image}
              alt=""
              sx={{ width: 76, height: 76, flexShrink: 0, borderRadius: "12px", backgroundColor: "#000" }}
            >
              <PhenomenonArt id={ph.id} />
            </Avatar>
            <Box>
              <Typography sx={{ fontSize: 16 }}>{ph.title}</Typography>
              <Typography sx={{ mt: 0.5, fontSize: 14, lineHeight: 1.4, color: "rgba(255,255,255,0.55)" }}>
                {ph.tagline}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
}