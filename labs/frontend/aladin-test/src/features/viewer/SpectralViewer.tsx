"use client";

import {useState} from "react";
import Alert from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import MenuDrawer from "@/features/menu/MenuDrawer";
import { SvgDefs } from "@/features/phenomena/SvgDefs";
import ControlPanel from "./components/ControlPanel";
import ViewerCanvas from "./components/ViewerCanvas";
import { FILTERS } from "./engine/filters";
import ViewerShell from "./components/ViewerShell";
import { useSpectralScene } from "./hooks/useSpectralScene";

export default function SpectralViewer() {
  // --- Estado de la interfaz ---
  const [filterIndex, setFilterIndex] = useState(0);
  const [inten, setInten] = useState(72); // aplicación del filtro (%)
  const [gain, setGain] = useState(110); // intensidad de luz (%)
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuSection, setMenuSection] = useState<number | null>(0);

  const filter = FILTERS[filterIndex];

    // Escena: carga, dibujo y errores viven en el hook.
  const { canvasRef, source, error, clearError, upload, reloadDemo } = useSpectralScene(filter, inten, gain);

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
          intensityDisabled={filter.fn === null} // sin filtro activo no hay nada que aplicar
          inten={inten}
          gain={gain}
          onInten={setInten}
          onGain={setGain}
          onUpload={upload}
          onDemo={reloadDemo}
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
              if (reason !== "clickaway") clearError();
            }}
            anchorOrigin={{ vertical: "top", horizontal: "center" }}
          >
            <Alert severity="error" variant="filled" onClose={() => clearError()}>
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