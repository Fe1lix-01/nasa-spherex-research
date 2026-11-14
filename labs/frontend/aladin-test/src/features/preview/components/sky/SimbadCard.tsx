"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import { eter, glassPanel } from "@/theme/theme";
import { getObjectDetails, type SimbadDetails, type SimbadObject } from "../../model/simbad";

type State =
  | { status: "loading" }
  | { status: "ready"; details: SimbadDetails }
  | { status: "empty" } // SIMBAD no devolvió ficha para este objeto
  | { status: "error" };

// Memoria corta de fichas ya consultadas: volver a elegir un objeto no repite la consulta.
const cache = new Map<number, SimbadDetails | null>();

/* ------------------------------ formato ------------------------------ */

const pad = (n: number) => String(n).padStart(2, "0");
const fmt = (v: number, digits = 2) => v.toLocaleString("es-MX", { maximumFractionDigits: digits });
const MONO = 'ui-monospace, "SF Mono", Menlo, Consolas, monospace';
const LY_PER_PC = 3.26156;

/** Ascensión recta en horas, minutos y segundos. Se redondea en enteros para que nunca salga "60.00 s". */
function formatRa(deg: number) {
  const total = Math.round((((deg % 360) + 360) % 360) / 15 * 3600 * 100); // centésimas de segundo
  const hh = Math.floor(total / 360000) % 24;
  const mm = Math.floor((total % 360000) / 6000);
  const ss = (total % 6000) / 100;
  return `${pad(hh)}h ${pad(mm)}m ${ss.toFixed(2).padStart(5, "0")}s`;
}

/** Declinación en grados, minutos y segundos de arco. */
function formatDec(deg: number) {
  const total = Math.round(Math.abs(deg) * 3600 * 10); // décimas de segundo de arco
  const dd = Math.floor(total / 36000);
  const mm = Math.floor((total % 36000) / 600);
  const ss = (total % 600) / 10;
  return `${deg < 0 ? "−" : "+"}${pad(dd)}° ${pad(mm)}′ ${ss.toFixed(1).padStart(4, "0")}″`;
}

/** SIMBAD antepone "NAME " a los nombres comunes ("NAME Barnard's star"). */
const prettyName = (id: string) => id.replace(/^NAME\s+/, "").replace(/\s+/g, " ").trim();

/** Distancia a partir del paralaje. Con menos de 1 mas el error es demasiado grande para mostrarla. */
function distanceLabel(parallaxMas?: number) {
  if (parallaxMas === undefined || parallaxMas < 1) return undefined;
  const ly = (1000 / parallaxMas) * LY_PER_PC;
  return `≈ ${ly < 100 ? fmt(ly, 2) : fmt(Math.round(ly), 0)} años luz`;
}

/* ------------------------------ piezas ------------------------------ */

function Row({ label, mono, children }: { label: string; mono?: boolean; children: ReactNode }) {
  return (
    <Box sx={{ mt: 1.75 }}>
      <Box sx={{ fontSize: 12, color: eter.textMuted }}>{label}</Box>
      <Box sx={{ mt: 0.25, fontSize: 13.5, color: "#fff", fontFamily: mono ? MONO : undefined }}>{children}</Box>
    </Box>
  );
}

/* ------------------------------ tarjeta ------------------------------ */

/**
 * Ficha de SIMBAD del objeto elegido. Se cierra con la X, con Escape o al hacer clic en el cielo vacío
 * (eso último lo hace el hook al recibir un clic sin objeto). El padre la monta con `key={oid}`, así
 * cada objeto nuevo empieza con su propio estado.
 */
export default function SimbadCard({ object, onClose }: { object: SimbadObject; onClose: () => void }) {
  const [state, setState] = useState<State>(() => {
    const hit = cache.get(object.oid);
    return hit === undefined ? { status: "loading" } : hit ? { status: "ready", details: hit } : { status: "empty" };
  });
  const [attempt, setAttempt] = useState(0);

  // Escape cierra; el ref evita volver a registrar el listener cada vez que cambia `onClose`.
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRef.current();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Pide la ficha completa. Si se cierra o se elige otro objeto a medias, se cancela la petición.
  useEffect(() => {
    if (cache.has(object.oid)) return;
    const controller = new AbortController();
    getObjectDetails(object.oid, controller.signal)
      .then((details) => {
        cache.set(object.oid, details);
        setState(details ? { status: "ready", details } : { status: "empty" });
      })
      .catch(() => {
        if (!controller.signal.aborted) setState({ status: "error" });
      });
    return () => controller.abort();
  }, [object.oid, attempt]);

  const d = state.status === "ready" ? state.details : null;
  const ra = d?.ra ?? object.ra;
  const dec = d?.dec ?? object.dec;
  const distance = distanceLabel(d?.parallaxMas);
  const mags = d ? Object.entries(d.magnitudes) : [];
  const hasPm = d?.pmRaMasYr !== undefined && d?.pmDecMasYr !== undefined;

  return (
    <Box
      role="dialog"
      aria-label="Información de SIMBAD"
      sx={{
        ...glassPanel,
        backgroundColor: "rgba(12,18,28,0.72)", // más opaco que el panel: aquí hay texto sobre estrellas brillantes
        position: "absolute",
        left: 16,
        top: 64,
        width: "min(340px, calc(100% - 32px))",
        // Arriba empieza a 64 px y abajo se reservan ~300 px para el selector de modo y el reproductor,
        // así la tarjeta nunca queda debajo de ellos; lo que no cabe se desplaza dentro de la tarjeta.
        maxHeight: "max(180px, calc(100% - 364px))",
        overflowY: "auto",
        scrollbarWidth: "thin",
        scrollbarColor: "rgba(255,255,255,0.28) transparent",
        borderRadius: "16px",
        p: 2.25,
        color: "#fff",
        pointerEvents: "auto", // la capa de encima del mapa no recibe clics; la tarjeta sí
        animation: "simbadCardIn 180ms ease-out",
        "@keyframes simbadCardIn": {
          from: { opacity: 0, transform: "translateY(6px)" },
          to: { opacity: 1, transform: "none" },
        },
        "@media (prefers-reduced-motion: reduce)": { animation: "none" },
      }}
    >
      {/* Encabezado: nombre, tipo y botón de cerrar */}
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Box sx={{ fontSize: 18, fontWeight: 600, lineHeight: 1.25, wordBreak: "break-word" }}>
            {prettyName(object.id)}
          </Box>
          <Box sx={{ mt: 0.5, fontSize: 13, color: eter.accent }}>{d?.typeLabel ?? object.otype}</Box>
        </Box>
        <Box
          component="button"
          type="button"
          aria-label="Cerrar"
          onClick={onClose}
          sx={{
            all: "unset",
            cursor: "pointer",
            width: 28,
            height: 28,
            borderRadius: "8px",
            display: "grid",
            placeItems: "center",
            color: eter.textMuted,
            "&:hover": { color: "#fff", backgroundColor: eter.hoverFill },
            "&:focus-visible": { outline: `2px solid ${eter.focusRing}` },
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M2 2l10 10M12 2L2 12" />
          </svg>
        </Box>
      </Box>

      <Row label="Coordenadas (ICRS)" mono>
        {formatRa(ra)} · {formatDec(dec)}
        <Box sx={{ mt: 0.25, fontSize: 12, color: eter.textMuted }}>
          {ra.toFixed(5)}° · {dec.toFixed(5)}°
        </Box>
      </Row>

      {state.status === "loading" && (
        <Box
          sx={{
            mt: 2,
            fontSize: 13,
            color: eter.textMuted,
            animation: "simbadPulse 1.4s ease-in-out infinite",
            "@keyframes simbadPulse": { "0%,100%": { opacity: 0.5 }, "50%": { opacity: 1 } },
          }}
        >
          Consultando SIMBAD…
        </Box>
      )}

      {state.status === "error" && (
        <Box sx={{ mt: 2, fontSize: 13 }}>
          <Box sx={{ color: eter.danger }}>No se pudo consultar SIMBAD. Revisa tu conexión e inténtalo de nuevo.</Box>
          <Box
            component="button"
            type="button"
            onClick={() => {
              setState({ status: "loading" });
              setAttempt((n) => n + 1);
            }}
            sx={{
              all: "unset",
              cursor: "pointer",
              mt: 1,
              px: 1.5,
              py: 0.5,
              borderRadius: "8px",
              border: `1px solid ${eter.lineStrong}`,
              "&:hover": { borderColor: eter.lineHover, backgroundColor: eter.hoverFill },
              "&:focus-visible": { outline: `2px solid ${eter.focusRing}` },
            }}
          >
            Reintentar
          </Box>
        </Box>
      )}

      {state.status === "empty" && (
        <Box sx={{ mt: 2, fontSize: 13, color: eter.textMuted }}>SIMBAD no tiene más datos de este objeto.</Box>
      )}

      {d && (
        <>
          {d.spectralType && <Row label="Tipo espectral">{d.spectralType}</Row>}
          {distance && (
            <Row label="Distancia (por paralaje)">
              {distance}
              <Box component="span" sx={{ color: eter.textMuted }}> · {fmt(d.parallaxMas!, 2)} mas</Box>
            </Row>
          )}
          {hasPm && (
            <Row label="Movimiento propio (RA, Dec)" mono>
              {fmt(d.pmRaMasYr!)} , {fmt(d.pmDecMasYr!)} mas/año
            </Row>
          )}
          {d.radialVelocityKmS !== undefined && (
            <Row label="Velocidad radial" mono>
              {fmt(d.radialVelocityKmS)} km/s
            </Row>
          )}
          {mags.length > 0 && (
            <Row label="Magnitudes">
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mt: 0.25 }}>
                {mags.map(([band, value]) => (
                  <Box
                    key={band}
                    sx={{ px: 1, py: 0.25, borderRadius: "999px", border: `1px solid ${eter.lineStrong}`, fontSize: 12, fontFamily: MONO }}
                  >
                    {band} {value!.toFixed(2)}
                  </Box>
                ))}
              </Box>
            </Row>
          )}
          {d.nbref > 0 && <Row label="Citado en">{d.nbref.toLocaleString("es-MX")} artículos</Row>}
        </>
      )}

      {/* Pie: enlace a la ficha completa y crédito de los datos */}
      <Box sx={{ mt: 2.25, pt: 1.5, borderTop: `1px solid ${eter.line}`, display: "flex", justifyContent: "space-between", gap: 1, fontSize: 12 }}>
        <Box
          component="a"
          href={`https://simbad.harvard.edu/simbad/sim-id?Ident=%40${object.oid}`}
          target="_blank"
          rel="noopener noreferrer"
          sx={{ color: eter.accent, textDecoration: "none", "&:hover": { textDecoration: "underline" } }}
        >
          Ver en SIMBAD ↗
        </Box>
        <Box sx={{ color: eter.textFaint }}>Datos: SIMBAD (CDS)</Box>
      </Box>
    </Box>
  );
}