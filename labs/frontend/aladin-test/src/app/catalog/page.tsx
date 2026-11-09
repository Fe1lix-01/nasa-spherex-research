"use client";

/**
 * Página del catálogo astronómico de ÉTER.
 *
 * Consulta los objetos reales de ETER API y muestra sus
 * observaciones junto con los metadatos de los archivos FITS.
 *
 * Esta página es independiente del visor de demostración.
 */

import { useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";

import { eter } from "@/theme/theme";
import { eterApiService } from "@/services/eter-api";

import type {
  AstronomicalObjectDetail,
  AstronomicalObjectSummary,
  FrameMetadata,
} from "@/contracts/api";

/**
 * Convierte los errores de las peticiones en mensajes legibles.
 */
function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado al consultar la API.";
}

export default function CatalogPage() {
  // Datos principales del catálogo y los metadatos FITS.
  const [objects, setObjects] = useState<AstronomicalObjectSummary[]>([]);
  const [frames, setFrames] = useState<FrameMetadata[]>([]);

  // Identificador y detalle del objeto seleccionado.
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedObject, setSelectedObject] =
    useState<AstronomicalObjectDetail | null>(null);

  // Estados independientes para controlar las peticiones.
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [framesError, setFramesError] = useState<string | null>(null);

  // Permite volver a consultar los datos desde el botón Actualizar.
  const [reloadKey, setReloadKey] = useState(0);

  /**
   * Consulta el catálogo y los metadatos FITS al montar la página.
   *
   * Promise.allSettled permite mostrar los objetos aunque falle
   * temporalmente la consulta de metadatos, o viceversa.
   */
  useEffect(() => {
    let active = true;

    async function loadCatalog() {
      setLoading(true);
      setError(null);
      setFramesError(null);

      const [objectsResult, framesResult] = await Promise.allSettled([
        eterApiService.getObjects(),
        eterApiService.getFrames(),
      ]);

      // Evita actualizar el estado si el componente ya se desmontó.
      if (!active) return;

      if (objectsResult.status === "fulfilled") {
        const catalogObjects = objectsResult.value.objects;

        setObjects(catalogObjects);

        // Conserva la selección si sigue existiendo; de lo contrario,
        // selecciona automáticamente el primer objeto disponible.
        setSelectedId((current) => {
          if (current && catalogObjects.some((item) => item.id === current)) {
            return current;
          }

          return catalogObjects[0]?.id ?? null;
        });
      } else {
        setObjects([]);
        setSelectedId(null);
        setError(getErrorMessage(objectsResult.reason));
      }

      if (framesResult.status === "fulfilled") {
        setFrames(framesResult.value.frames);
      } else {
        setFrames([]);
        setFramesError(getErrorMessage(framesResult.reason));
      }

      setLoading(false);
    }

    void loadCatalog();

    return () => {
      active = false;
    };
  }, [reloadKey]);

  /**
   * Consulta el detalle cuando cambia el objeto seleccionado.
   */
  useEffect(() => {
    if (!selectedId) {
      setSelectedObject(null);
      setDetailLoading(false);
      setDetailError(null);
      return;
    }

    let active = true;

    async function loadObjectDetail() {
      setDetailLoading(true);
      setDetailError(null);

      try {
        const result = await eterApiService.getObject(selectedId!);

        if (active) {
          setSelectedObject(result);
        }
      } catch (error) {
        if (active) {
          setSelectedObject(null);
          setDetailError(getErrorMessage(error));
        }
      } finally {
        if (active) {
          setDetailLoading(false);
        }
      }
    }

    void loadObjectDetail();

    return () => {
      active = false;
    };
  }, [selectedId, reloadKey]);

  // Estilos compartidos para las superficies del catálogo.
  const panelStyle = {
    bgcolor: eter.panel,
    border: `1px solid ${eter.line}`,
    borderRadius: 3,
  };

  return (
    <Box
      component="main"
      sx={{
        width: "100%",
        height: "100dvh",
        overflowY: "auto",
        bgcolor: eter.ink,
        color: "#fff",
        px: { xs: 2, md: 4 },
        py: { xs: 3, md: 4 },
      }}
    >
      <Box sx={{ maxWidth: 1440, mx: "auto" }}>
        {/* Encabezado principal del catálogo. */}
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={2}
          sx={{ mb: 3 }}
        >
          <Box>
            <Typography
              variant="overline"
              sx={{ color: eter.textFaint, letterSpacing: 2 }}
            >
              ÉTER / EXPLORACIÓN
            </Typography>

            <Typography
              variant="h4"
              sx={{ fontWeight: 600, mt: 0.5 }}
            >
              Catálogo astronómico
            </Typography>

            <Typography
              variant="body2"
              sx={{ color: eter.textMuted, mt: 1 }}
            >
              Explora los objetos y las observaciones disponibles de SPHEREx.
            </Typography>
          </Box>

          <Button
            variant="outlined"
            onClick={() => setReloadKey((value) => value + 1)}
            disabled={loading || detailLoading}
            sx={{
              color: "#fff",
              borderColor: eter.lineStrong,
              "&:hover": {
                borderColor: eter.accent,
                bgcolor: eter.hoverFill,
              },
            }}
          >
            Actualizar
          </Button>
        </Stack>

        {/* Indicadores generales de los datos recibidos. */}
        <Stack direction="row" spacing={1} sx={{ mb: 3 }} flexWrap="wrap">
          <Chip
            label={`${objects.length} objetos`}
            sx={{
              bgcolor: eter.card,
              color: "#fff",
              border: `1px solid ${eter.line}`,
            }}
          />

          <Chip
            label={`${frames.length} frames FITS`}
            sx={{
              bgcolor: eter.card,
              color: "#fff",
              border: `1px solid ${eter.line}`,
            }}
          />
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            No se pudo cargar el catálogo: {error}
          </Alert>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              lg: "340px minmax(0, 1fr)",
            },
            gap: 2,
            alignItems: "start",
          }}
        >
          {/* Panel izquierdo: listado de objetos. */}
          <Card elevation={0} sx={panelStyle}>
            <Box sx={{ p: 2.5 }}>
              <Typography variant="h6" sx={{ mb: 0.5 }}>
                Objetos disponibles
              </Typography>

              <Typography
                variant="caption"
                sx={{ color: eter.textMuted }}
              >
                Selecciona un objeto para consultar sus observaciones.
              </Typography>

              <Divider sx={{ borderColor: eter.line, my: 2 }} />

              {loading ? (
                <Stack alignItems="center" sx={{ py: 4 }}>
                  <CircularProgress size={26} />
                </Stack>
              ) : objects.length === 0 ? (
                <Typography
                  variant="body2"
                  sx={{ color: eter.textMuted, py: 2 }}
                >
                  No hay objetos disponibles.
                </Typography>
              ) : (
                <Stack spacing={1.25}>
                  {objects.map((object) => {
                    const selected = selectedId === object.id;

                    return (
                      <Card
                        key={object.id}
                        elevation={0}
                        sx={{
                          bgcolor: selected
                            ? "rgba(255,210,76,0.08)"
                            : eter.card,
                          border: `1px solid ${
                            selected ? eter.accent : eter.line
                          }`,
                          borderRadius: 2,
                        }}
                      >
                        <CardActionArea
                          onClick={() => setSelectedId(object.id)}
                          aria-pressed={selected}
                          sx={{ p: 1.5 }}
                        >
                          <Stack spacing={1}>
                            <Typography
                              variant="subtitle2"
                              sx={{
                                color: selected ? eter.accent : "#fff",
                                overflowWrap: "anywhere",
                              }}
                            >
                              {object.name}
                            </Typography>

                            <Typography
                              variant="caption"
                              sx={{ color: eter.textMuted }}
                            >
                              {object.observation_count} observaciones
                            </Typography>

                            <Stack
                              direction="row"
                              spacing={0.5}
                              flexWrap="wrap"
                              useFlexGap
                            >
                              {object.detectors.map((detector) => (
                                <Chip
                                  key={detector}
                                  label={detector}
                                  size="small"
                                  sx={{
                                    height: 22,
                                    bgcolor: eter.glass,
                                    color: eter.textMuted,
                                    fontSize: 10,
                                  }}
                                />
                              ))}
                            </Stack>
                          </Stack>
                        </CardActionArea>
                      </Card>
                    );
                  })}
                </Stack>
              )}
            </Box>
          </Card>

          {/* Panel derecho: detalle y metadatos del objeto seleccionado. */}
          <Card elevation={0} sx={panelStyle}>
            <Box sx={{ p: { xs: 2, md: 3 } }}>
              {detailLoading ? (
                <Stack
                  alignItems="center"
                  spacing={2}
                  sx={{ py: 8 }}
                >
                  <CircularProgress size={30} />
                  <Typography
                    variant="body2"
                    sx={{ color: eter.textMuted }}
                  >
                    Consultando observaciones...
                  </Typography>
                </Stack>
              ) : detailError ? (
                <Alert severity="error">
                  No se pudo cargar el detalle: {detailError}
                </Alert>
              ) : !selectedObject ? (
                <Typography sx={{ color: eter.textMuted }}>
                  Selecciona un objeto para consultar su información.
                </Typography>
              ) : (
                <>
                  <Typography
                    variant="overline"
                    sx={{ color: eter.textFaint, letterSpacing: 1.5 }}
                  >
                    OBJETO SELECCIONADO
                  </Typography>

                  <Typography
                    variant="h5"
                    sx={{
                      fontWeight: 600,
                      mt: 0.5,
                      overflowWrap: "anywhere",
                    }}
                  >
                    {selectedObject.name}
                  </Typography>

                  <Typography
                    variant="body2"
                    sx={{ color: eter.textMuted, mt: 1 }}
                  >
                    {selectedObject.observation_count} observaciones
                    disponibles en los detectores{" "}
                    {selectedObject.detectors.join(", ")}.
                  </Typography>

                  <Divider sx={{ borderColor: eter.line, my: 3 }} />

                  <Typography variant="h6" sx={{ mb: 2 }}>
                    Observaciones y metadatos FITS
                  </Typography>

                  {framesError && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      No se pudieron consultar los metadatos FITS:{" "}
                      {framesError}
                    </Alert>
                  )}

                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: {
                        xs: "1fr",
                        md: "repeat(2, minmax(0, 1fr))",
                      },
                      gap: 1.5,
                    }}
                  >
                    {selectedObject.observations.map((observation) => {
                      // Relaciona cada observación con sus metadatos
                      // mediante el nombre real del archivo FITS.
                      const frame = frames.find(
                        (item) =>
                          item.filename === observation.filename ||
                          item.id === observation.id,
                      );

                      return (
                        <Card
                          key={observation.id}
                          elevation={0}
                          sx={{
                            bgcolor: eter.card,
                            border: `1px solid ${eter.line}`,
                            borderRadius: 2,
                          }}
                        >
                          <Box sx={{ p: 2 }}>
                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="center"
                              sx={{ mb: 1.5 }}
                            >
                              <Typography
                                variant="subtitle1"
                                sx={{
                                  color: eter.accent,
                                  fontWeight: 600,
                                }}
                              >
                                Detector {observation.detector}
                              </Typography>

                              <Chip
                                label={observation.format}
                                size="small"
                                sx={{
                                  bgcolor: eter.glass,
                                  color: eter.textMuted,
                                }}
                              />
                            </Stack>

                            <Typography
                              variant="caption"
                              sx={{
                                display: "block",
                                color: eter.textMuted,
                                overflowWrap: "anywhere",
                                mb: 2,
                              }}
                            >
                              {observation.filename}
                            </Typography>

                            {frame ? (
                              <Stack spacing={1}>
                                <Divider
                                  sx={{ borderColor: eter.line }}
                                />

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Dimensiones:{" "}
                                  </Box>
                                  {frame.width} × {frame.height} px
                                </Typography>

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Centro RA:{" "}
                                  </Box>
                                  {frame.center_ra_deg.toFixed(6)}°
                                </Typography>

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Centro DEC:{" "}
                                  </Box>
                                  {frame.center_dec_deg.toFixed(6)}°
                                </Typography>

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Escala de píxel:{" "}
                                  </Box>
                                  {frame.pixel_scale_x_arcsec.toFixed(3)} ×{" "}
                                  {frame.pixel_scale_y_arcsec.toFixed(3)}{" "}
                                  arcsec/px
                                </Typography>

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Campo de visión:{" "}
                                  </Box>
                                  {frame.fov_x_deg.toFixed(5)} ×{" "}
                                  {frame.fov_y_deg.toFixed(5)}°
                                </Typography>

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Sistema:{" "}
                                  </Box>
                                  {frame.coordinate_system}
                                </Typography>

                                <Typography variant="body2">
                                  <Box
                                    component="span"
                                    sx={{ color: eter.textMuted }}
                                  >
                                    Proyección:{" "}
                                  </Box>
                                  {frame.projection}
                                </Typography>
                              </Stack>
                            ) : (
                              <Alert severity="warning">
                                No se encontraron metadatos para este archivo.
                              </Alert>
                            )}
                          </Box>
                        </Card>
                      );
                    })}
                  </Box>

                  <Alert
                    severity="info"
                    sx={{ mt: 3 }}
                  >
                    Actualmente la API proporciona metadatos de los archivos
                    FITS. Para visualizar las imágenes necesitamos conectar
                    posteriormente un endpoint de imagen renderizada.
                  </Alert>
                </>
              )}
            </Box>
          </Card>
        </Box>
      </Box>
    </Box>
  );
}
