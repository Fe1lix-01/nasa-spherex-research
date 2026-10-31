"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import MenuDrawer from "@/features/menu/MenuDrawer";
import { SvgDefs } from "@/features/phenomena/SvgDefs";
import ControlPanel from "./components/ControlPanel";
import ViewerCanvas from "./components/ViewerCanvas";
import { DEMO_IMAGE_URL, H, W } from "./constants";
import { FILTERS } from "./engine/filters";
import { createLayers, generateScene } from "./engine/generateScene";
import { loadImageIntoLayers, loadUrlIntoLayers } from "./engine/imageLayers";
import { renderLayers } from "./engine/render";
import type { Layers } from "./types";
import ViewerShell from "./components/ViewerShell";

type Source = "demo" | "upload";

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
    <ViewerShell
      // Fondo: hoy es el canvas con filtros; alex podrá pasar aquí el mosaico de Aladin.
      background={<ViewerCanvas canvasRef={canvasRef} />}
      // Panel de controles de abajo (filtros, sliders, subir imagen...).
      controls={
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
      }
      // Elementos que flotan sobre todo. SvgDefs va aquí porque lo usa el menú
      // (las ilustraciones de fenómenos), así el marco no depende de esa carpeta.
      overlays={
        <>
          <SvgDefs />

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
        </>
      }
      filterLabel={`${filter.name} · ${filter.band}`}
      sourceLabel={sourceLabel}
      menuOpen={menuOpen}
      onOpenMenu={() => openMenu(menuSection ?? 0)}
    />
  );
}