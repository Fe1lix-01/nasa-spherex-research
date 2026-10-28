"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import Close from "@mui/icons-material/Close";
import ExpandMore from "@mui/icons-material/ExpandMore";
import HelpOutlined from "@mui/icons-material/HelpOutlined";
import Tune from "@mui/icons-material/Tune";
import { ABOUT, FILTERS_INTRO, FOOTER_NOTE, PHENOMENA_INTRO } from "@/features/menu/content";
import type { FilterDef } from "@/features/viewer/types";
import { eter } from "@/theme/theme";
import { OrbitIcon } from "../../components/icons/CustomIcons";
import { PHENOMENA } from "@/features/phenomena/data";
import PhenomenonArt from "@/features/phenomena/PhenomenonArt";

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

const eyebrow = {
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.14em",
  color: "text.disabled",
} as const;

/* ---------- Contenido de cada sección ---------- */

function AboutContent() {
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

function FiltersContent({ filters, active }: { filters: FilterDef[]; active: number }) {
  return (
    <Box>
      <Typography sx={{ fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.7)" }}>{FILTERS_INTRO}</Typography>
      <Box component="ul" sx={{ listStyle: "none", p: 0, m: 0, mt: 3 }}>
        {filters.map((f, i) => {
          const on = i === active;
          return (
            <Box
              component="li"
              key={f.id}
              sx={{ py: 2, borderBottom: `1px solid ${eter.line}`, "&:last-of-type": { borderBottom: 0 } }}
            >
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 1.5 }}>
                <Typography
                  component="p"
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    fontSize: 16,
                    color: on ? "primary.main" : "text.primary",
                  }}
                >
                  {on && (
                    <Box
                      component="span"
                      sx={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "primary.main" }}
                    />
                  )}
                  {f.name}
                </Typography>
                <Typography sx={{ flexShrink: 0, fontSize: 14, color: "text.disabled" }}>{f.band}</Typography>
              </Box>
              <Typography sx={{ mt: 0.75, fontSize: 15, lineHeight: 1.7, color: "rgba(255,255,255,0.6)" }}>
                {f.desc}
                {on && " Banda activa del visor."}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

function PhenomenaContent() {
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
  // Referencias como estado: el contenido del Drawer se monta un instante después de abrir.
  const [bodyEl, setBodyEl] = useState<HTMLDivElement | null>(null);
  const [innerEl, setInnerEl] = useState<HTMLDivElement | null>(null);
  const [more, setMore] = useState(false); // ¿hay contenido por debajo? (muestra la flecha ↓)

  const check = useCallback(() => {
    if (!bodyEl) return;
    setMore(bodyEl.scrollHeight - bodyEl.scrollTop - bodyEl.clientHeight > 12);
  }, [bodyEl]);

  // Al cambiar de sección vuelve arriba.
  useEffect(() => {
    bodyEl?.scrollTo({ top: 0 });
  }, [section, bodyEl]);

  // Recalcula la flecha cuando cambia el alto del contenido (acordeón animándose, resize).
  useEffect(() => {
    if (!bodyEl || !innerEl || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(check);
    ro.observe(bodyEl);
    ro.observe(innerEl);
    check();
    return () => ro.disconnect();
  }, [bodyEl, innerEl, check]);

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
                  {i === 0 && <AboutContent />}
                  {i === 1 && <FiltersContent filters={filters} active={activeFilter} />}
                  {i === 2 && <PhenomenaContent />}
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
            onClick={() => bodyEl?.scrollBy({ top: 240, behavior: "smooth" })}
            sx={{ color: "rgba(255,255,255,0.6)" }}
          >
            <ArrowDownward />
          </IconButton>
        )}
      </Box>
    </Drawer>
  );
}
