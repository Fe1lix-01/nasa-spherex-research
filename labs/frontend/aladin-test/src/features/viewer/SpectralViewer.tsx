"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Snackbar from "@mui/material/Snackbar";
import Typography from "@mui/material/Typography";
import FiberManualRecord from "@mui/icons-material/FiberManualRecord";
import { DEMO_IMAGE_URL, H, W } from "@/features/viewer/constants";
import { FILTERS } from "./engine/filters";
import { renderLayers } from "@/features/viewer/engine/render";
import { createLayers, generateScene } from "@/features/viewer/engine/generateScene";
import { loadImageIntoLayers, loadUrlIntoLayers } from "@/features/viewer/engine/imageLayers";
import type { Layers } from "@/features/viewer/types";
import { eter } from "@/theme/theme";
import ControlPanel from "./components/ControlPanel";
import { CrosshairIcon } from "../../components/icons/CustomIcons";
import MenuDrawer from "../menu/MenuDrawer";
import { SvgDefs } from "@/features/phenomena/SvgDefs";
type Source = "demo" | "upload";
import ViewerHeader from "./components/ViewerHeader";
import ViewerTagline from "./components/ViewerTagline";

export default function SpectralViewer() {
  // --- Estado de la interfaz ---
  const [filterIndex, setFilterIndex] = useState(0);
  const [inten, setInten] = useState(72); // aplicación del filtro (%)
  const [gain, setGain] = useState(110); // intensidad de luz (%)
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);
  const [source, setSource] = useState<Source>("demo");
  const [sceneVersion, setSceneVersion] = useState(0); // sube cada vez que cambian los datos
  const [error, setError] = useState<string | null>(null);

  // --- Datos y lienzo (no provocan render al cambiar) ---
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const layersRef = useRef<Layers | null>(null);
  const imageRef = useRef<ImageData | null>(null);

  const filter = FILTERS[filterIndex];

  // Dibuja la imagen con los valores actuales.
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const layers = layersRef.current;
    if (!canvas || !layers) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (!imageRef.current) imageRef.current = ctx.createImageData(W, H);
    renderLayers(ctx, imageRef.current, layers, filter, inten, gain);
  }, [filter, inten, gain]);

  // Carga la escena demo: usa /public/escena-demo.jpg si existe; si no, genera una simulada.
  const loadDemo = useCallback(async (layers: Layers, isCancelled: () => boolean = () => false) => {
    try {
      await loadUrlIntoLayers(DEMO_IMAGE_URL, layers);
    } catch {
      if (isCancelled()) return;
      generateScene(layers);
    }
    if (isCancelled()) return;
    setSource("demo");
    setSceneVersion((v) => v + 1);
  }, []);

  // Al montar: crea las capas y carga la escena demo.
  useEffect(() => {
    let cancelled = false;
    const layers = createLayers();
    layersRef.current = layers;
    loadDemo(layers, () => cancelled);
    return () => {
      cancelled = true;
    };
  }, [loadDemo]);

  // Cada vez que cambia filtro, sliders o datos: vuelve a dibujar (máx. una vez por frame).
  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw, sceneVersion]);

  const handleUpload = async (file: File) => {
    if (!layersRef.current) return;
    try {
      await loadImageIntoLayers(file, layersRef.current);
      setSource("upload");
      setSceneVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      setError("No se pudo cargar la imagen. Prueba con otro archivo.");
    }
  };

  const handleDemo = () => {
    if (layersRef.current) loadDemo(layersRef.current);
  };

  const openMenu = (section: number) => {
    setMenuSection(section);
    setMenuOpen(true);
  };

  const sourceLabel = source === "demo" ? "Escena demo" : "Imagen subida";

  return (
    <Box component="main" sx={{ position: "relative", height: "100%", width: "100%", overflow: "hidden" }}>
      <SvgDefs />

      {/* IMAGEN: ocupa toda la pantalla y se recorta (cover) en cualquier tamaño */}
      <canvas
        ref={canvasRef}
        width={W}
        height={H}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
      />

      {/* Sombras suaves para que el texto se lea sobre cualquier imagen */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          background: "linear-gradient(to bottom, rgba(0,0,0,0.5), transparent 30%, transparent 60%, rgba(0,0,0,0.5))",
        }}
      />

      {/* Retícula central */}
      <CrosshairIcon
        sx={{
          pointerEvents: "none",
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          fontSize: 28,
          color: "rgba(255,255,255,0.4)",
        }}
      />

      {/* Encabezado */}
<ViewerHeader
  filterLabel={`${filter.name} · ${filter.band}`}
  menuOpen={menuOpen}
  onOpenMenu={() => openMenu(menuSection ?? 0)}
/>

      {/* Zona inferior: frase + panel de controles */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: { lg: "center" },
          gap: 2,
          p: { xs: 2, sm: 3 },
          pb: { xs: "max(16px, env(safe-area-inset-bottom))", lg: 5 },
        }}
      >
<ViewerTagline sourceLabel={sourceLabel} />

        <Box sx={{ pointerEvents: "auto", width: { xs: "100%", lg: "56%" }, maxWidth: { lg: 896 } }}>
          <ControlPanel
            filters={FILTERS}
            current={filterIndex}
            onSelect={setFilterIndex}
            inten={inten}
            gain={gain}
            onInten={setInten}
            onGain={setGain}
            onUpload={handleUpload}
            onDemo={handleDemo}
            onHelp={() => openMenu(1)}
            isDemo={source === "demo"}
          />
        </Box>
      </Box>

      {/* Menú lateral */}
      <MenuDrawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        section={menuSection}
        onSection={setMenuSection}
        filters={FILTERS}
        activeFilter={filterIndex}
        sourceLabel={sourceLabel}
      />

      {/* Aviso de error al subir imagen */}
      <Snackbar
        open={error !== null}
        autoHideDuration={5000}
        onClose={(_, reason) => {
          if (reason !== "clickaway") setError(null);
        }}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
      >
        <Alert severity="error" variant="filled" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
}
