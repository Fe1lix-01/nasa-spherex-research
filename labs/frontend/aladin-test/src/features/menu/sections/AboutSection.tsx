import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { OrbitIcon } from "@/components/icons/CustomIcons";
import { ABOUT } from "@/features/menu/content";
import { eter } from "@/theme/theme";
import { eyebrow } from "./styles";


export default function AboutSection() {
  return (
    <Box>
      <Typography sx={eyebrow}>{ABOUT.eyebrow}</Typography>
      <Typography component="h3" sx={{ mt: 1.5, fontSize: 28, lineHeight: 1.2 }}>
        {ABOUT.title}
      </Typography>
      <Typography sx={{ mt: 2, fontSize: 15, lineHeight: 1.7, color: "text.secondary" }}>{ABOUT.intro}</Typography>

      <Box
        sx={{
          mt: 2.5,
          p: 2.5,
          borderRadius: "16px",
          border: "1px solid rgba(255,255,255,0.12)",
          backgroundColor: eter.card,
        }}
      >
        <Typography sx={{ fontSize: 14 }}>{ABOUT.noteTitle}</Typography>
        <Typography sx={{ mt: 1, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.6)" }}>
          {ABOUT.note}
        </Typography>
      </Box>

      <Typography sx={{ mt: 2.5, fontSize: 15, lineHeight: 1.7, color: "text.secondary" }}>{ABOUT.body}</Typography>

      <Box sx={{ mt: 2.5, display: "flex", alignItems: "center", gap: 1.5 }}>
        <OrbitIcon sx={{ fontSize: 28, color: "rgba(255,255,255,0.55)" }} />
        <Box>
          <Typography sx={{ fontSize: 15 }}>{ABOUT.mission}</Typography>
          <Typography sx={{ fontSize: 14, color: "text.disabled" }}>{ABOUT.missionSub}</Typography>
        </Box>
      </Box>
    </Box>
  );
}