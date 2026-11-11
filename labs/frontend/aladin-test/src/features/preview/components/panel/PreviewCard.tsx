"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import type { Epoch, MovingObject } from "@/contracts";
import { KIND_LABELS } from "@/features/preview/model/labels";

type Props = {
  object: MovingObject;
  epochs: Epoch[];
  onClose: () => void;
};

/**
 * Recuadro flotante arriba de la imagen con la información básica del candidato
 * y la estructura lista para las tres épocas y la animación de movimiento.
 *
 * Se posiciona en la esquina superior derecha para no tapar el panel de controles
 * de abajo. Se puede cerrar con la "✕".
 */
export default function PreviewCard({ object, epochs, onClose }: Props) {
  const kindLabel = KIND_LABELS[object.kind] ?? object.kind;
  const name = object.name ?? object.id;
  const detectedIds = new Set(object.positions.map((p) => p.epochId));
  const latest = object.positions[object.positions.length - 1];
  const ready = object.positions.length >= 2; // con 2 posiciones ya se puede dibujar movimiento

  return (
    <Box
      sx={{
        position: "absolute",
        top: { xs: 76, sm: 92 }, // debajo del encabezado del visor
        right: { xs: 12, sm: 20 },
        width: { xs: "min(340px, calc(100vw - 24px))", sm: 340 },
        bgcolor: "rgba(10, 12, 20, 0.88)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(255, 213, 79, 0.45)",
        borderRadius: 2,
        p: 2,
        pointerEvents: "auto",
        zIndex: 3,
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        gap: 1.5,
        maxHeight: "calc(100vh - 110px)", // si no cabe en pantalla, se desplaza por dentro
        overflowY: "auto",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
      }}
    >
      {/* Encabezado: nombre, tipo y botón de cerrar */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600, lineHeight: 1.2 }}>
            {name}
          </Typography>
          <Typography variant="caption" sx={{ color: "#FFD54F" }}>
            {kindLabel}
          </Typography>
        </Box>
        <IconButton
          size="small"
          onClick={onClose}
          aria-label="Cerrar"
          sx={{ color: "#fff", mt: -0.5, mr: -0.5 }}
        >
          <Box component="span" sx={{ fontSize: 18, lineHeight: 1 }}>
            ✕
          </Box>
        </IconButton>
      </Box>

      {/* Explicación breve del candidato */}
      {object.summary && (
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.8)", lineHeight: 1.45 }}>
          {object.summary}
        </Typography>
      )}

      {/* Última posición conocida */}
      {latest && (
        <Box>
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.6)" }}>
            Última posición
          </Typography>
          <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
            RA {latest.ra.toFixed(4)}° · Dec {latest.dec.toFixed(4)}°
          </Typography>
        </Box>
      )}

      {/* Espacio reservado para la animación de las 3 épocas */}
      <Box
        sx={{
          aspectRatio: "16 / 9",
          bgcolor: "rgba(255,255,255,0.04)",
          border: "1px dashed rgba(255,255,255,0.2)",
          borderRadius: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 1,
          textAlign: "center",
        }}
      >
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)" }}>
          Animación de las 3 épocas
          <br />
          (pendiente de cargar imágenes)
        </Typography>
      </Box>

      {/* Lista de épocas: qué se detectó y qué falta */}
      <Box>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.6)", display: "block", mb: 0.5 }}>
          Detectado en {object.positions.length} de {epochs.length} épocas
        </Typography>
        <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
          {epochs.map((ep) => {
            const on = detectedIds.has(ep.id);
            return (
              <Box
                key={ep.id}
                sx={{
                  px: 1,
                  py: 0.25,
                  borderRadius: 1,
                  fontSize: 12,
                  border: "1px solid",
                  borderColor: on ? "#FFD54F" : "rgba(255,255,255,0.15)",
                  color: on ? "#FFD54F" : "rgba(255,255,255,0.4)",
                  bgcolor: on ? "rgba(255,213,79,0.08)" : "transparent",
                }}
              >
                {on ? "●" : "○"} {ep.label}
              </Box>
            );
          })}
        </Box>
      </Box>

      {/* Predicción, si existe */}
      {object.prediction && (
        <Box
          sx={{
            p: 1,
            borderRadius: 1,
            bgcolor: "rgba(255,213,79,0.06)",
            border: "1px solid rgba(255,213,79,0.2)",
          }}
        >
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.6)" }}>
            Predicción para {object.prediction.atDate}
          </Typography>
          <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 12 }}>
            RA {object.prediction.ra.toFixed(4)}° · Dec {object.prediction.dec.toFixed(4)}°
          </Typography>
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.5)" }}>
            ± {object.prediction.uncertaintyArcsec}″ · confianza {Math.round(object.prediction.confidence * 100)}%
          </Typography>
        </Box>
      )}

      {/* Acción principal: desactivada hasta que haya 2 o 3 imágenes cargadas */}
      <Tooltip title={ready ? "Pendiente de cargar las imágenes de las épocas restantes" : "Faltan posiciones para animar"}>
        <span>
          <Button variant="outlined" size="small" disabled fullWidth>
            Reproducir movimiento
          </Button>
        </span>
      </Tooltip>
    </Box>
  );
}