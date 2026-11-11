"use client";

import { useState, type SyntheticEvent } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { styled } from "@mui/material/styles";
import type { MovingObject } from "@/contracts";
import { KIND_LABELS } from "../labels";

type Props = {
  objects: MovingObject[];
  /** "" = nada elegido, "custom" = coordenadas buscadas, o el id de un candidato. */
  value: string;
  onPickCandidate: (id: string) => void;
  onPickRegion: (ra: number, dec: number, fovDeg: number) => void;
  onSearch: (ra: number, dec: number) => void;
  onReset: () => void;
  onInfo: () => void;
  disabled?: boolean;
};

const CHEVRON = `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'><path d='M1 1l5 5 5-5' fill='none' stroke='%23baa3ff' stroke-width='2'/></svg>")`;

const SelectBox = styled("select")({
  height: 39,
  maxWidth: "min(270px, 75vw)",
  padding: "0 42px 0 14px",
  borderRadius: 9,
  border: "1px solid #3b4567",
  backgroundColor: "#171e33",
  color: "#fafaff",
  fontSize: 13,
  cursor: "pointer",
  appearance: "none",
  WebkitAppearance: "none",
  backgroundImage: CHEVRON,
  backgroundRepeat: "no-repeat",
  backgroundPosition: "right 14px center",
  "&:hover": { borderColor: "#baa3ff", backgroundColor: "#202842" },
  "&:focus-visible": { outline: "2px solid #baa3ff", outlineOffset: 2 },
  "& option": { backgroundColor: "#171e33", color: "#fafaff" },
});

const FieldInput = styled("input")({
  boxSizing: "border-box",
  width: "100%",
  padding: "9px 10px",
  border: "1px solid #515e80",
  borderRadius: 8,
  backgroundColor: "#1a2339",
  color: "#fff",
  fontSize: 13,
  "&:focus-visible": { outline: "2px solid #baa3ff" },
});

const buttonSx = {
  height: 39,
  minWidth: 0,
  px: 1.75,
  borderRadius: "9px",
  border: "1px solid #3b4567",
  backgroundColor: "#171e33",
  color: "#fafaff",
  fontSize: 13,
  fontWeight: 400,
  textTransform: "none",
  "&:hover": { borderColor: "#baa3ff", backgroundColor: "#202842" },
} as const;

const REGIONS = [
  { id: "center", name: "Centro galáctico", ra: 266.4168, dec: -29.0078, fovDeg: 40 },
  { id: "orion", name: "Nebulosa de Orión", ra: 83.8221, dec: -5.3911, fovDeg: 5 },
  { id: "m101", name: "Galaxia M101", ra: 210.8023, dec: 54.3489, fovDeg: 1.5 },
  { id: "all", name: "Todo el cielo", ra: 0, dec: 0, fovDeg: 360 },
  { id: "barnard", name: "Estrella de Barnard", ra: 269.44627, dec: 4.76820, fovDeg: 0.25 },
];

/**

 * selector de candidatos + Coordenadas + Reiniciar visor + Información.
 */
export default function TopRightTools({ objects, value, onPickCandidate, onPickRegion, onSearch, onReset, onInfo, disabled }: Props) {
  const [panelOpen, setPanelOpen] = useState(false);
  const [ra, setRa] = useState("");
  const [dec, setDec] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = (e: SyntheticEvent) => {
    e.preventDefault();
    const r = Number(ra);
    const d = Number(dec);
    if (ra.trim() === "" || dec.trim() === "" || Number.isNaN(r) || Number.isNaN(d)) {
      setError("Escribe RA y Dec en grados, por ejemplo 209.42 y 53.94.");
      return;
    }
    if (r < 0 || r >= 360 || d < -90 || d > 90) {
      setError("RA entre 0 y 360, Dec entre -90 y 90.");
      return;
    }
    setError(null);
    onSearch(r, d);
    setPanelOpen(false);
  };

  return (
    <Box
      sx={{
        position: "absolute",
        zIndex: 3,
        top: { xs: 132, sm: 36 },
        left: { xs: 16, sm: "auto" },
        right: { xs: 16, sm: 96 }, // a la izquierda del botón de tres rayitas
        maxWidth: { sm: "calc(100vw - 420px)" }, // no se encima con el título
        display: "flex",
        flexWrap: "wrap",
        gap: 1.125,
        justifyContent: { xs: "flex-start", sm: "flex-end" },
      }}
    >
      <SelectBox
        aria-label="Candidato o región"
        value={value}
        onChange={(e) => {
          const id = e.target.value;
          const region = REGIONS.find((item) => `region:${item.id}` === id);

          if (region) {
            onPickRegion(region.ra, region.dec, region.fovDeg);
          } else if (id) {
            onPickCandidate(id);
          }
        }}
      >
        {value === "" && (
          <option value="" disabled>
            Elegir candidato o región
          </option>
        )}

        {value === "custom" && (
          <option value="custom" disabled>
            Ubicación personalizada
          </option>
        )}

        {objects.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name ?? o.id} · {KIND_LABELS[o.kind] ?? o.kind}
          </option>
        ))}

        <optgroup label="Regiones">
          {REGIONS.map((region) => (
            <option key={region.id} value={`region:${region.id}`}>
              {region.name}
            </option>
          ))}
        </optgroup>
      </SelectBox>

      <Button disabled={disabled} onClick={() => setPanelOpen((o) => !o)} sx={buttonSx}>
        Coordenadas
      </Button>
      <Button
        onClick={() => {
          setPanelOpen(false);
          onReset();
        }}
        sx={buttonSx}
      >
        Reiniciar visor
      </Button>
      <Button onClick={onInfo} sx={buttonSx}>
        Información
      </Button>

      {panelOpen && (
        <Box
          component="form"
          onSubmit={submit}
          sx={{
            position: "absolute",
            top: "calc(100% + 10px)",
            right: 0,
            width: "min(320px, calc(100vw - 32px))",
            boxSizing: "border-box",
            p: 2.5,
            border: "1px solid #616b91",
            borderRadius: "16px",
            backgroundColor: "rgba(17,24,42,0.94)",
            boxShadow: "0 18px 55px rgba(0,0,0,0.6)",
            color: "#f5f5fc",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Typography sx={{ fontSize: 16, fontWeight: 700 }}>Buscar coordenadas</Typography>
            <IconButton size="small" aria-label="Cerrar" onClick={() => setPanelOpen(false)} sx={{ color: "#fff" }}>
              <Box component="span" sx={{ fontSize: 16, lineHeight: 1 }}>
                ✕
              </Box>
            </IconButton>
          </Box>
          <Typography sx={{ fontSize: 13, color: "#bac5e0", mt: 0.5 }}>Sistema ICRS, coordenadas en grados.</Typography>

          <Box component="label" sx={{ display: "grid", gap: 0.625, mt: 1.5, fontSize: 13, color: "#c7d0ec" }}>
            Ascensión recta (RA)
            <FieldInput inputMode="decimal" value={ra} onChange={(e) => setRa(e.target.value)} />
          </Box>
          <Box component="label" sx={{ display: "grid", gap: 0.625, mt: 1.5, fontSize: 13, color: "#c7d0ec" }}>
            Declinación (Dec)
            <FieldInput inputMode="decimal" value={dec} onChange={(e) => setDec(e.target.value)} />
          </Box>

          {error && (
            <Typography role="alert" sx={{ fontSize: 13, color: "#ffc1cb", mt: 1 }}>
              {error}
            </Typography>
          )}

          <Button
            type="submit"
            fullWidth
            sx={{
              mt: 2,
              py: 1.25,
              borderRadius: "8px",
              backgroundColor: "#8566dc",
              color: "#fff",
              fontWeight: 700,
              textTransform: "none",
              "&:hover": { backgroundColor: "#9878e3" },
            }}
          >
            Explorar ubicación
          </Button>
        </Box>
      )}
    </Box>
  );
}