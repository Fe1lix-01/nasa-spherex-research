"use client";

import { useState, type CSSProperties, type FormEvent } from "react";
import AladinBackground from "../../features/sky-viewer/AladinBackground";
import {
  ALLWISE_HIPS_URL,
  validateSkyOptions,
} from "../../features/sky-viewer/aladinDocument";
import type { SkyPosition } from "../../features/sky-viewer/types";

type Region = {
  id: string;
  name: string;
  position: SkyPosition;
  fovDeg: number;
};

// 1. REGIONES. Cambia estas coordenadas para crear nuevos destinos.
const REGIONS: Region[] = [
  { id: "center", name: "Centro galáctico", position: { raDeg: 266.4168, decDeg: -29.0078 }, fovDeg: 40 },
  { id: "orion", name: "Nebulosa de Orión", position: { raDeg: 83.8221, decDeg: -5.3911 }, fovDeg: 5 },
  { id: "m101", name: "Galaxia M101", position: { raDeg: 210.8023, decDeg: 54.3489 }, fovDeg: 1.5 },
  { id: "all", name: "Todo el cielo", position: { raDeg: 0, decDeg: 0 }, fovDeg: 360 },
];

// 2. ESTILOS. Están AQUÍ para evitar depender de un archivo CSS externo.
const styles: Record<string, CSSProperties> = {
  page: {
    position: "fixed",
    inset: 0,
    width: "100%",
    height: "100dvh",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    background: "#040712",
    color: "#f8f8ff",
    fontFamily: "Arial, Helvetica, sans-serif",
  },
  header: {
    flex: "0 0 auto", // El encabezado usa solo la altura que necesita.
    minHeight: 94,
    boxSizing: "border-box",
    padding: "16px 28px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: "16px 24px",
    background: "#0a0e1c",
    borderBottom: "1px solid #252c48",
    zIndex: 2,
  },
  title: {
    fontSize: "clamp(23px, 2.1vw, 31px)",
    fontWeight: 750,
    lineHeight: 1.1,
    margin: 0,
    letterSpacing: "0.035em",
  },
  subtitle: {
    fontSize: 12,
    margin: "7px 0 0",
    color: "#adb6d4",
  },
  controls: {
    display: "flex",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 9,
  },
  select: {
    height: 39,
    maxWidth: "min(270px, 75vw)",
    padding: "0 13px",
    borderRadius: 9,
    border: "1px solid #3b4567",
    background: "#171e33",
    color: "#fafaff",
    fontSize: 13,
    cursor: "pointer",
  },
  button: {
    height: 39,
    padding: "0 14px",
    border: "1px solid #3b4567",
    borderRadius: 9,
    background: "#171e33",
    color: "#fafaff",
    fontSize: 13,
    cursor: "pointer",
  },
  viewer: {
    position: "relative",
    flex: "1 1 0%", // TODA la altura que sobra es para el mosaico.
    minHeight: 0,      // Evita el alto predeterminado del iframe (150px).
    width: "100%",
    overflow: "hidden",
    background: "#03050a",
  },
  sky: {
    position: "absolute",
    inset: 0, // Equivale a top/right/bottom/left: 0.
    width: "100%",
    height: "100%",
  },
  attribution: {
    position: "absolute",
    right: 18,
    bottom: 15,
    zIndex: 2,
    padding: "8px 12px",
    borderRadius: 8,
    border: "1px solid #ffffff30",
    background: "#090d1ccc",
    color: "#cdd5ee",
    fontSize: 11,
    pointerEvents: "none",
  },
  panel: {
    position: "absolute",
    top: 20,
    right: 20,
    zIndex: 3,
    boxSizing: "border-box",
    width: "min(350px, calc(100% - 40px))",
    maxHeight: "calc(100% - 40px)",
    padding: 20,
    overflowY: "auto",
    border: "1px solid #616b91",
    borderRadius: 16,
    background: "#11182aef",
    boxShadow: "0 18px 55px #0009",
    color: "#f5f5fc",
    fontSize: 13,
    lineHeight: 1.6,
  },
  panelHeading: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    marginBottom: 10,
  },
  field: {
    display: "grid",
    gap: 5,
    marginTop: 11,
    color: "#c7d0ec",
  },
  input: {
    boxSizing: "border-box",
    width: "100%",
    padding: "9px 10px",
    border: "1px solid #515e80",
    borderRadius: 8,
    background: "#1a2339",
    color: "white",
  },
  primary: {
    width: "100%",
    marginTop: 15,
    padding: "11px 12px",
    border: 0,
    borderRadius: 8,
    background: "#8566dc",
    color: "white",
    fontWeight: 700,
    cursor: "pointer",
  },
};

export default function SkyTestPage() {
  // 3. ESTADOS. React controla la región y los paneles.
  const [region, setRegion] = useState<Region>(REGIONS[0]);
  const [revision, setRevision] = useState(0);
  const [panel, setPanel] = useState<"coordinates" | "info" | null>(null);
  const [ra, setRa] = useState(String(REGIONS[0].position.raDeg));
  const [dec, setDec] = useState(String(REGIONS[0].position.decDeg));
  const [fov, setFov] = useState(String(REGIONS[0].fovDeg));
  const [error, setError] = useState("");

  function chooseRegion(id: string) {
    const next = REGIONS.find((item) => item.id === id);
    if (!next) return;
    setRegion(next);
    setRa(String(next.position.raDeg));
    setDec(String(next.position.decDeg));
    setFov(String(next.fovDeg));
    setError("");
  }

  function goToCoordinates(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ra.trim() || !dec.trim() || !fov.trim()) {
      setError("Completa los tres campos.");
      return;
    }
    const position = { raDeg: Number(ra), decDeg: Number(dec) };
    const fovDeg = Number(fov);
    const validation = validateSkyOptions({ ...position, fovDeg, surveyUrl: ALLWISE_HIPS_URL });
    if (validation) {
      setError(validation);
      return;
    }
    setRegion({ id: "custom", name: "Ubicación personalizada", position, fovDeg });
    setError("");
    setPanel(null);
  }

  return (
    <main style={styles.page}>
      {/* 4. ENCABEZADO: está arriba del mosaico, NO encima de él. */}
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>
            PROJECT <span style={{ color: "#baa3ff" }}>MORLEY</span>
          </h1>
          <p style={styles.subtitle}>Exploración astronómica interactiva</p>
        </div>

        <nav style={styles.controls} aria-label="Herramientas de exploración">
          <select
            aria-label="Región astronómica"
            style={styles.select}
            value={region.id}
            onChange={(event) => chooseRegion(event.target.value)}
          >
            {region.id === "custom" && <option value="custom">Ubicación personalizada</option>}
            {REGIONS.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
          <button style={styles.button} type="button" onClick={() => setPanel(panel === "coordinates" ? null : "coordinates")}>
            Coordenadas
          </button>
          <button style={styles.button} type="button" onClick={() => setRevision((n) => n + 1)}>
            Reiniciar visor
          </button>
          <button style={styles.button} type="button" onClick={() => setPanel(panel === "info" ? null : "info")}>
            Información
          </button>
        </nav>
      </header>

      {/* 5. VISOR: llena TODO el espacio restante debajo del encabezado. */}
      <section style={styles.viewer} aria-label="Mosaico infrarrojo interactivo del cielo">
        <div style={styles.sky}>
          <AladinBackground
            key={revision}
            position={region.position}
            fovDeg={region.fovDeg}
            surveyUrl={ALLWISE_HIPS_URL}
            style={{ display: "block", width: "100%", height: "100%", border: 0 }}
            title="Mapa del cielo infrarrojo AllWISE"
          />
        </div>

        <div style={styles.attribution}>
          AllWISE / IRSA · Aladin Lite · {region.name}
        </div>

        {panel === "coordinates" && (
          <form style={styles.panel} onSubmit={goToCoordinates}>
            <div style={styles.panelHeading}>
              <strong style={{ fontSize: 16 }}>Buscar coordenadas</strong>
              <button type="button" style={styles.button} onClick={() => setPanel(null)} aria-label="Cerrar">✕</button>
            </div>
            <p style={{ color: "#bac5e0" }}>Sistema ICRS, coordenadas en grados.</p>
            <label style={styles.field}>
              Ascensión recta (RA)
              <input style={styles.input} type="number" step="any" value={ra} onChange={(e) => setRa(e.target.value)} />
            </label>
            <label style={styles.field}>
              Declinación (Dec)
              <input style={styles.input} type="number" step="any" value={dec} onChange={(e) => setDec(e.target.value)} />
            </label>
            <label style={styles.field}>
              Campo de visión (FOV)
              <input style={styles.input} type="number" step="any" value={fov} onChange={(e) => setFov(e.target.value)} />
            </label>
            {error && <p role="alert" style={{ color: "#ffc1cb" }}>{error}</p>}
            <button type="submit" style={styles.primary}>Explorar ubicación</button>
          </form>
        )}

        {panel === "info" && (
          <aside style={styles.panel}>
            <div style={styles.panelHeading}>
              <strong style={{ fontSize: 16 }}>Sobre este visor</strong>
              <button type="button" style={styles.button} onClick={() => setPanel(null)} aria-label="Cerrar">✕</button>
            </div>
            <p>Explora el cielo infrarrojo con datos AllWISE, servidos por IRSA y visualizados mediante Aladin Lite.</p>
            <p style={{ color: "#bac5e0" }}>
              Esta capa es una referencia astronómica. Aún no corresponde al mosaico SPHEREx ni muestra detección de movimiento.
            </p>
          </aside>
        )}
      </section>
    </main>
  );
}
