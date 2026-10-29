"use client";

import { FOOTER_NOTE } from "@/features/menu/content";
import type { ReactNode } from "react";
import { useScrollHint } from "./hooks/useScrollHint";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import Close from "@mui/icons-material/Close";
import ExpandMore from "@mui/icons-material/ExpandMore";
import HelpOutlined from "@mui/icons-material/HelpOutlined";
import Tune from "@mui/icons-material/Tune";
import type { FilterDef } from "@/features/viewer/types";
import { eter } from "@/theme/theme";
import { OrbitIcon } from "../../components/icons/CustomIcons";
import AboutSection from "./sections/AboutSection";
import FiltersSection from "./sections/FiltersSection";
import PhenomenaSection from "./sections/PhenomenaSection";
import { eyebrow } from "./sections/styles";



type Props = {
  open: boolean;
  onClose: () => void;
  /** Sección abierta (0, 1, 2) o null si todas están cerradas. */
  section: number | null;
  onSection: (section: number | null) => void;
  filters: FilterDef[];
  activeFilter: number;
  /** Texto del pie, por ejemplo "Escena demo". */
  sourceLabel: string;
};

const SECTIONS: { title: string; icon: ReactNode }[] = [
  { title: "¿Quiénes somos?", icon: <HelpOutlined /> },
  { title: "¿Qué hace cada filtro?", icon: <Tune /> },
  { title: "Fenómenos y cuerpos celestes", icon: <OrbitIcon /> },
];

/* ---------- Panel lateral ---------- */

export default function MenuDrawer({
  open,
  onClose,
  section,
  onSection,
  filters,
  activeFilter,
  sourceLabel,
}: Props) {
  const { setBodyEl, setInnerEl, more, check, scrollDown } = useScrollHint(section);
  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose} // se llama con Escape y con clic en el fondo
      sx={{
        "& .MuiBackdrop-root": { backgroundColor: "rgba(0,0,0,0.65)" },
        "& .MuiDrawer-paper": {
          width: { xs: "94%", sm: 420 },
          maxWidth: "100%",
          display: "flex",
          flexDirection: "column",
          backgroundColor: eter.panel,
          backgroundImage: "none",
          borderLeft: `1px solid ${eter.line}`,
          boxShadow: "0 25px 50px -12px rgba(0,0,0,0.6)",
        },
      }}
    >
      {/* Encabezado */}
      <Box
        sx={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          px: { xs: 2.5, sm: 3 },
          py: 2.5,
          borderBottom: `1px solid ${eter.line}`,
        }}
      >
        <Box>
          <Typography sx={eyebrow}>ÉTER / Guía del visor</Typography>
          <Typography component="h2" sx={{ mt: 0.5, fontSize: 32, fontWeight: 500, lineHeight: 1 }}>
            Menú
          </Typography>
        </Box>
        <IconButton
          onClick={onClose}
          aria-label="Cerrar menú"
          sx={{
            width: 48,
            height: 48,
            borderRadius: "12px",
            border: `1px solid ${eter.lineStrong}`,
            backgroundColor: "rgba(255,255,255,0.03)",
          }}
        >
          <Close />
        </IconButton>
      </Box>

      {/* Cuerpo: tres acordeones controlados (solo uno abierto a la vez) */}
      <Box ref={setBodyEl} onScroll={check} sx={{ flex: 1, minHeight: 0, overflowY: "auto", px: { xs: 2.5, sm: 3 } }}>
        <Box ref={setInnerEl}>
          {SECTIONS.map(({ title, icon }, i) => {
            const isOpen = section === i;
            return (
              <Accordion
                key={title}
                expanded={isOpen}
                onChange={(_, expanded) => onSection(expanded ? i : null)}
                disableGutters
                square
                elevation={0}
                sx={{
                  backgroundColor: "transparent",
                  backgroundImage: "none",
                  borderBottom: `1px solid ${eter.line}`,
                  "&:before": { display: "none" },
                  "&:last-of-type": { borderBottom: 0 },
                }}
              >
                <AccordionSummary
                  expandIcon={<ExpandMore />}
                  sx={{
                    px: 0,
                    minHeight: 72,
                    "&.Mui-expanded": { minHeight: 72 },
                    color: isOpen ? "primary.main" : "text.primary",
                    "& .MuiAccordionSummary-content": { my: 0, alignItems: "center", gap: 2, fontSize: 17 },
                    "& .MuiAccordionSummary-expandIconWrapper": {
                      color: isOpen ? "primary.main" : "rgba(255,255,255,0.55)",
                    },
                  }}
                >
                  <Box sx={{ display: "flex", color: isOpen ? "primary.main" : "rgba(255,255,255,0.55)" }}>{icon}</Box>
                  <Box component="span">{title}</Box>
                </AccordionSummary>
                <AccordionDetails sx={{ px: 0, pt: 0.5, pb: 3 }}>
                    {i === 0 && <AboutSection />}
                    {i === 1 && <FiltersSection filters={filters} active={activeFilter} />}
                    {i === 2 && <PhenomenaSection />}
                </AccordionDetails>
              </Accordion>
            );
          })}
        </Box>
      </Box>

      {/* Pie fijo */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          px: { xs: 2.5, sm: 3 },
          py: 2,
          borderTop: `1px solid ${eter.line}`,
        }}
      >
        <Box>
          <Typography sx={{ fontSize: 13, color: "rgba(255,255,255,0.8)" }}>
            {sourceLabel} · Visualización ilustrativa
          </Typography>
          <Typography sx={{ mt: 0.25, fontSize: 11, color: "text.disabled" }}>{FOOTER_NOTE}</Typography>
        </Box>
        {more && (
          <IconButton
            aria-label="Ver más"
            onClick={scrollDown}
            sx={{ color: "rgba(255,255,255,0.6)" }}
          >
            <ArrowDownward />
          </IconButton>
        )}
      </Box>
    </Drawer>
  );
}
