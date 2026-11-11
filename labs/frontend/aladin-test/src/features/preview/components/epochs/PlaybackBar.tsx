"use client";

import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Slider from "@mui/material/Slider";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import PauseRoundedIcon from "@mui/icons-material/PauseRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import type { Epoch } from "@/contracts";
import { eter } from "@/theme/theme";
import { dateAt } from "@/features/preview/model/trajectory";

type Props = {
  epochs: Epoch[];
  t: number;
  playing: boolean;
  speed: number;
  onToggle: () => void;
  onSeek: (t: number) => void;
  onSpeed: (speed: number) => void;
};

const SPEEDS = [0.5, 1, 2];

/** Barra de reproducción: play/pausa, línea de tiempo con las épocas, fecha y velocidad. */
export default function PlaybackBar({ epochs, t, playing, speed, onToggle, onSeek, onSpeed }: Props) {
  const last = Math.max(epochs.length - 1, 0);

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: { xs: 1, sm: 2 },
        px: 2,
        pt: 1,
        pb: 0.5,
        color: "#fff",
        bgcolor: eter.panelGlass,
        border: `1px solid ${eter.lineStrong}`,
        borderRadius: 3,
        maxWidth: { lg: 680 }, // para que no quede debajo del recuadro del candidato
        backdropFilter: "blur(10px)",
      }}
    >
      <IconButton
        aria-label={playing ? "Pausar" : "Reproducir"}
        onClick={onToggle}
        sx={{
          width: 40,
          height: 40,
          color: eter.onAccent,
          bgcolor: eter.accent,
          "&:hover": { bgcolor: eter.accent, filter: "brightness(1.1)" },
        }}
      >
        {playing ? <PauseRoundedIcon /> : <PlayArrowRoundedIcon />}
      </IconButton>

      <Box sx={{ flex: 1, minWidth: 0, px: 1.5, pb: 1.5 }}>
        <Slider
          size="small"
          aria-label="Línea de tiempo"
          min={0}
          max={last}
          step={0.001}
          value={t}
          onChange={(_, value) => onSeek(value as number)}
          marks={epochs.map((e, i) => ({ value: i, label: e.label }))}
          sx={{
            // Sin transición: el valor cambia en cada fotograma y, con la transición de MUI,
            // la bolita se queda rezagada respecto a la fecha y al marcador.
            "& .MuiSlider-thumb, & .MuiSlider-track": { transition: "none" },
            "& .MuiSlider-rail": { bgcolor: eter.rail, opacity: 1 },
            "& .MuiSlider-markLabel": { color: eter.textFaint, fontSize: 11 },
            "& .MuiSlider-mark": { bgcolor: eter.lineHover },
          }}
        />
      </Box>

      <Typography sx={{ fontFamily: "monospace", fontSize: 13, minWidth: 84, textAlign: "right", color: eter.accent }}>
        {dateAt(epochs, t)}
      </Typography>

      <ToggleButtonGroup
        exclusive
        size="small"
        value={speed}
        onChange={(_, value: number | null) => {
          if (value !== null) onSpeed(value);
        }}
        aria-label="Velocidad"
        sx={{ display: { xs: "none", sm: "flex" }, mb: 0.5 }}
      >
        {SPEEDS.map((s) => (
          <ToggleButton
            key={s}
            value={s}
            sx={{
              px: 1,
              py: 0.25,
              fontSize: 12,
              color: eter.textMuted,
              borderColor: eter.lineStrong,
              "&.Mui-selected": { color: eter.accent, bgcolor: eter.accentGlow },
            }}
          >
            {s}×
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Box>
  );
}