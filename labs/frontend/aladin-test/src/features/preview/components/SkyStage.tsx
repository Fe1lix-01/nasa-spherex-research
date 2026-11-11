"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import { ALADIN_SCRIPT_URL, ALLWISE_HIPS_URL } from "@/features/sky-viewer/aladinDocument";

/* ------------------------------------------------------------------ */
/* Aladin Lite, cargado desde la misma URL que usa el visor de Felix  */
/* ------------------------------------------------------------------ */

type AladinView = {
  gotoRaDec: (ra: number, dec: number) => void;
  setFoV: (fovDeg: number) => void;
  world2pix: (ra: number, dec: number) => number[] | null | undefined;
  showReticle: (show: boolean) => void;
};

type AladinApi = {
  init: Promise<unknown>;
  aladin: (element: string | HTMLElement, options: Record<string, unknown>) => AladinView;
  HiPS: (url: string, options?: Record<string, unknown>) => unknown;
};

declare global {
  interface Window {
    __MORLEY_ALADIN__?: AladinApi;
  }
}

let loading: Promise<AladinApi> | null = null;

/** Descarga Aladin Lite una sola vez. Se inyecta un script para no depender del empaquetador. */
function loadAladin(): Promise<AladinApi> {
  if (window.__MORLEY_ALADIN__) return Promise.resolve(window.__MORLEY_ALADIN__);
  if (loading) return loading;

  loading = new Promise<AladinApi>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error("La descarga de Aladin Lite tardó demasiado.")), 45000);
    window.addEventListener(
      "morley-aladin-ready",
      () => {
        window.clearTimeout(timer);
        const api = window.__MORLEY_ALADIN__;
        if (api) resolve(api);
        else reject(new Error("Aladin Lite no se inicializó."));
      },
      { once: true },
    );
    window.addEventListener(
      "morley-aladin-error",
      () => {
        window.clearTimeout(timer);
        reject(new Error("No se pudo descargar Aladin Lite desde jsDelivr."));
      },
      { once: true },
    );
    const script = document.createElement("script");
    script.textContent =
      `import(${JSON.stringify(ALADIN_SCRIPT_URL)})` +
      `.then(function(m){window.__MORLEY_ALADIN__=m.default;window.dispatchEvent(new Event("morley-aladin-ready"));})` +
      `.catch(function(){window.dispatchEvent(new Event("morley-aladin-error"));});`;
    document.head.appendChild(script);
  });
  loading.catch(() => {
    loading = null; // permite reintentar si falló
  });
  return loading;
}

/* ------------------------------------------------------------------ */
/* Componente                                                          */
/* ------------------------------------------------------------------ */

export type SkyMarker = { id: string; label: string; ra: number; dec: number };
export type SkyTrailPoint = { ra: number; dec: number; index: number };

type Props = {
  /** Si es false el mapa sigue cargado pero oculto (así no se vuelve a crear al cambiar de modo). */
  active: boolean;
  /** A dónde mira el mapa. `nonce` cambia en cada búsqueda para volver a ir aunque sea al mismo punto. */
  target: { raDeg: number; decDeg: number; fovDeg: number; nonce: number };
  /** Aproximación de color del filtro elegido, solo para el mosaico. */
  cssFilter: string;
  /** Zona del cielo que cubren las imágenes de prueba. */
  patch: { ra: number; dec: number; fovDeg: number; label: string };
  /** Las imágenes de prueba (se pintan encima del mosaico, en su zona del cielo). */
  patchContent: ReactNode;
  markers: SkyMarker[];
  trail: SkyTrailPoint[];
  /** Instante de la animación, para rellenar los puntos del rastro ya recorridos. */
  t: number;
  onFail: (message: string) => void;
};

type Pt = { x: number; y: number };
type Scene = {
  patch: { cx: number; cy: number; width: number } | null;
  markers: (SkyMarker & Pt)[];
  trail: (SkyTrailPoint & Pt)[];
};

// Alto de la franja del encabezado: el mapa empieza debajo, así sus controles no tapan el título.
const TOP_OFFSET = 88;
// Tamaño base del lienzo de las imágenes de prueba (el mismo del canvas del visor).
const PATCH_W = 1280;
const PATCH_H = 720;

/**
 * Mosaico de Aladin montado directamente en la página (sin iframe). Eso permite:
 *  - ir a unas coordenadas sin recargar el mapa,
 *  - saber dónde cae un punto del cielo en pantalla (world2pix),
 *  - dibujar encima las imágenes de prueba, el marcador y el rastro, que siguen al mapa.
 */
export default function SkyStage({
  active,
  target,
  cssFilter,
  patch,
  patchContent,
  markers,
  trail,
  t,
  onFail,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<AladinView | null>(null);
  const [ready, setReady] = useState(false);
  const [scene, setScene] = useState<Scene>({ patch: null, markers: [], trail: [] });

  // Últimos valores, para que el ciclo de dibujo no se reinicie en cada render.
  const latest = useRef({ markers, trail, patch });
  const failRef = useRef(onFail);
  useEffect(() => {
    latest.current = { markers, trail, patch };
    failRef.current = onFail;
  });
  const firstTarget = useRef(target);

  // Crear el mapa (una sola vez).
  useEffect(() => {
    let cancelled = false;
    const host = hostRef.current;
    (async () => {
      try {
        const A = await loadAladin();
        await A.init;
        if (cancelled || !host) return;

        const root = new URL(ALLWISE_HIPS_URL, window.location.origin);
        root.pathname = root.pathname.replace(/\/?$/, "/");
        const check = await fetch(new URL("properties", root));
        if (!check.ok) throw new Error(`El servidor HiPS respondió HTTP ${check.status}.`);
        if (cancelled) return;

        host.innerHTML = "";
        const element = document.createElement("div");
        element.style.width = "100%";
        element.style.height = "100%";
        host.appendChild(element);

        const first = firstTarget.current;
        const view = A.aladin(element, {
          survey: A.HiPS(root.href),
          target: `${first.raDeg} ${first.decDeg}`,
          fov: first.fovDeg,
          projection: "AIT",
          cooFrame: "ICRSd",
          log: false,
          // Se intenta ocultar los controles que no usamos; si alguna opción no existe, se ignora.
          showLayersControl: false,
          showGotoControl: false,
          showShareControl: false,
          showFullscreenControl: false,
          showSettingsControl: false,
          showSimbadPointerControl: false,
          showCooGridControl: false,
          showFrame: false,
          showFov: false,
          showCooLocation: false,
          showProjectionControl: false,
          showStatusBar: false,
          showZoomControl: true,
        });
        try {
          view.showReticle(false); // el visor ya dibuja su propia retícula al centro
        } catch {
          /* no pasa nada si no existe */
        }
        viewRef.current = view;
        setReady(true);
      } catch (error) {
        if (!cancelled) failRef.current(error instanceof Error ? error.message : String(error));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Ir a donde pidan (búsqueda de coordenadas o candidato), sin recargar el mapa.
  useEffect(() => {
    const view = viewRef.current;
    if (!ready || !view) return;
    try {
      view.gotoRaDec(target.raDeg, target.decDeg);
      view.setFoV(target.fovDeg);
    } catch {
      /* ignorar */
    }
  }, [ready, target.raDeg, target.decDeg, target.fovDeg, target.nonce]);

  // Mientras está visible, seguir al mapa: calcular dónde cae cada cosa en pantalla.
  useEffect(() => {
    if (!ready || !active) return;
    let raf = 0;
    let lastKey = "";

    const tick = () => {
      const view = viewRef.current;
      if (view) {
        const project = (ra: number, dec: number): Pt | null => {
          try {
            const p = view.world2pix(ra, dec);
            return p && Number.isFinite(p[0]) && Number.isFinite(p[1]) ? { x: p[0], y: p[1] } : null;
          } catch {
            return null;
          }
        };

        const { markers: ms, trail: tr, patch: pa } = latest.current;
        const next: Scene = { patch: null, markers: [], trail: [] };

        const center = project(pa.ra, pa.dec);
        const north = project(pa.ra, pa.dec + 0.2);
        if (center && north) {
          const pixelsPerDegree = Math.hypot(north.x - center.x, north.y - center.y) / 0.2;
          const width = pa.fovDeg * pixelsPerDegree;
          if (width >= 4) next.patch = { cx: center.x, cy: center.y, width };
        }
        for (const m of ms) {
          const p = project(m.ra, m.dec);
          if (p) next.markers.push({ ...m, ...p });
        }
        for (const q of tr) {
          const p = project(q.ra, q.dec);
          if (p) next.trail.push({ ...q, ...p });
        }

        // Solo se vuelve a pintar si algo se movió al menos 0.1 px.
        const key = JSON.stringify(next, (_k, v) => (typeof v === "number" ? Math.round(v * 10) / 10 : v));
        if (key !== lastKey) {
          lastKey = key;
          setScene(next);
        }
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [ready, active]);

  const p = scene.patch;
  const patchHeight = p ? (p.width * PATCH_H) / PATCH_W : 0;
  const line = scene.trail.map((q) => `${q.x},${q.y}`).join(" ");

  return (
    <Box
      sx={{
        position: "absolute",
        inset: 0,
        visibility: active ? "visible" : "hidden",
        pointerEvents: active ? "auto" : "none",
      }}
    >
      <Box sx={{ position: "absolute", left: 0, right: 0, bottom: 0, top: TOP_OFFSET }}>
        {/* El mapa de Aladin; el filtro de color solo le afecta a él. */}
        <Box ref={hostRef} sx={{ position: "absolute", inset: 0, filter: cssFilter || "none" }} />

        {/* Todo lo que va encima del mapa. No bloquea el arrastre ni el zoom. */}
        <Box sx={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
          {p && (
            <>
              {/* Imágenes de prueba, en su zona del cielo */}
              <Box
                sx={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  width: PATCH_W,
                  height: PATCH_H,
                  transformOrigin: "0 0",
                  transform: `translate(${p.cx - p.width / 2}px, ${p.cy - patchHeight / 2}px) scale(${p.width / PATCH_W})`,
                }}
              >
                {patchContent}
              </Box>
              {/* Marco y nombre */}
              <Box
                sx={{
                  position: "absolute",
                  left: p.cx - p.width / 2,
                  top: p.cy - patchHeight / 2,
                  width: p.width,
                  height: patchHeight,
                  border: "1px dashed rgba(255,213,79,0.75)",
                  boxSizing: "border-box",
                }}
              >
                {p.width > 60 && (
                  <Box
                    component="span"
                    sx={{
                      position: "absolute",
                      left: 0,
                      top: -22,
                      px: 1,
                      py: 0.25,
                      fontSize: 12,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      color: "#FFD54F",
                      bgcolor: "rgba(10,12,20,0.8)",
                      borderRadius: 1,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {patch.label}
                  </Box>
                )}
              </Box>
            </>
          )}

          {scene.trail.length > 1 && (
            <svg width="100%" height="100%" style={{ position: "absolute", inset: 0 }}>
              <polyline
                points={line}
                fill="none"
                stroke="rgba(255,213,79,0.6)"
                strokeWidth={1.5}
                strokeDasharray="5 5"
              />
            </svg>
          )}
          {scene.trail.map((q) => (
            <Box
              key={q.index}
              sx={{
                position: "absolute",
                left: q.x,
                top: q.y,
                width: 8,
                height: 8,
                transform: "translate(-50%, -50%)",
                borderRadius: "50%",
                border: "1.5px solid #FFD54F",
                bgcolor: t >= q.index - 0.001 ? "#FFD54F" : "transparent",
              }}
            />
          ))}

          {scene.markers.map((m) => (
            <Box
              key={m.id}
              sx={{
                position: "absolute",
                left: m.x,
                top: m.y,
                width: 18,
                height: 18,
                transform: "translate(-50%, -50%)",
                border: "2px solid #FFD54F",
                borderRadius: "50%",
              }}
            >
              <Box
                component="span"
                sx={{
                  position: "absolute",
                  left: 22,
                  top: -4,
                  color: "#FFD54F",
                  fontSize: 12,
                  whiteSpace: "nowrap",
                  textShadow: "0 1px 6px rgba(0,0,0,0.8)",
                }}
              >
                {m.label}
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}
