"use client";

import { useState, type FormEvent } from "react";
import AladinBackground from "../../features/sky-viewer/AladinBackground";
import { ALLWISE_HIPS_URL, validateSkyOptions } from "../../features/sky-viewer/aladinDocument";
import type { SkyPosition } from "../../features/sky-viewer/types";
import styles from "./sky-test.module.css";

type Region = {
  id: string;
  name: string;
  position: SkyPosition;
  fovDeg: number;
};

const REGIONS: Region[] = [
  { id: "center", name: "Centro galáctico", position: { raDeg: 266.4168, decDeg: -29.0078 }, fovDeg: 40 },
  { id: "orion", name: "Nebulosa de Orión", position: { raDeg: 83.8221, decDeg: -5.3911 }, fovDeg: 5 },
  { id: "m101", name: "Galaxia M101", position: { raDeg: 210.8023, decDeg: 54.3489 }, fovDeg: 1.5 },
  { id: "all", name: "Todo el cielo", position: { raDeg: 0, decDeg: 0 }, fovDeg: 360 },
];

export default function SkyTestPage() {
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
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>
            PROJECT <span style={{ color: "#baa3ff" }}>MORLEY</span>
          </h1>
          <p className={styles.subtitle}>Exploración astronómica interactiva</p>
        </div>

        <nav className={styles.controls} aria-label="Herramientas de exploración">
          <div className={styles.regionSelect}>
            <select
              aria-label="Región astronómica"
              className={styles.select}
              value={region.id}
              onChange={(event) => chooseRegion(event.target.value)}
            >
              {region.id === "custom" && <option value="custom">Ubicación personalizada</option>}
              {REGIONS.map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
          </div>
          <button className={styles.button} type="button" onClick={() => setPanel(panel === "coordinates" ? null : "coordinates")}>
            Coordenadas
          </button>
          <button className={styles.button} type="button" onClick={() => setRevision((n) => n + 1)}>
            Reiniciar visor
          </button>
          <button className={styles.button} type="button" onClick={() => setPanel(panel === "info" ? null : "info")}>
            Información
          </button>
        </nav>
      </header>

      <section className={styles.viewer} aria-label="Mosaico infrarrojo interactivo del cielo">
        <div className={styles.sky}>
          <AladinBackground
            key={revision}
            position={region.position}
            fovDeg={region.fovDeg}
            surveyUrl={ALLWISE_HIPS_URL}
            style={{ display: "block", width: "100%", height: "100%", border: 0 }}
            title="Mapa del cielo infrarrojo AllWISE"
          />
        </div>

        <div className={styles.attribution}>
          AllWISE / IRSA · Aladin Lite · {region.name}
        </div>

        {panel === "coordinates" && (
          <form className={styles.panel} onSubmit={goToCoordinates}>
            <div className={styles.panelHeading}>
              <strong style={{ fontSize: 16 }}>Buscar coordenadas</strong>
              <button type="button" className={styles.button} onClick={() => setPanel(null)} aria-label="Cerrar">✕</button>
            </div>
            <p style={{ color: "#bac5e0" }}>Sistema ICRS, coordenadas en grados.</p>
            <label className={styles.field}>
              Ascensión recta (RA)
              <input className={styles.input} type="number" step="any" value={ra} onChange={(e) => setRa(e.target.value)} />
            </label>
            <label className={styles.field}>
              Declinación (Dec)
              <input className={styles.input} type="number" step="any" value={dec} onChange={(e) => setDec(e.target.value)} />
            </label>
            <label className={styles.field}>
              Campo de visión (FOV)
              <input className={styles.input} type="number" step="any" value={fov} onChange={(e) => setFov(e.target.value)} />
            </label>
            {error && <p role="alert" style={{ color: "#ffc1cb" }}>{error}</p>}
            <button type="submit" className={styles.primary}>Explorar ubicación</button>
          </form>
        )}

        {panel === "info" && (
          <aside className={styles.panel}>
            <div className={styles.panelHeading}>
              <strong style={{ fontSize: 16 }}>Sobre este visor</strong>
              <button type="button" className={styles.button} onClick={() => setPanel(null)} aria-label="Cerrar">✕</button>
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
