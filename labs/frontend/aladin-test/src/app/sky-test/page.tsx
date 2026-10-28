"use client";

import { useState } from "react";
import AladinBackground from "../../features/sky-viewer/AladinBackground";
import { ALLWISE_HIPS_URL } from "../../features/sky-viewer/aladinDocument";

const views = [
  { name: "Todo el cielo", position: { raDeg: 0, decDeg: 0 }, fovDeg: 360 },
  { name: "Centro galáctico", position: { raDeg: 266.4168, decDeg: -29.0078 }, fovDeg: 40 },
  { name: "M101", position: { raDeg: 210.8023, decDeg: 54.3489 }, fovDeg: 1.5 },
] as const;

export default function SkyTestPage() {
  const [viewIndex, setViewIndex] = useState(0);
  const [revision, setRevision] = useState(0);
  const [visible, setVisible] = useState(true);
  const view = views[viewIndex];

  return (
    <main style={{ minHeight: "100dvh", padding: 20, background: "#070a13", color: "#e5e9f2", fontFamily: "system-ui, sans-serif" }}>
      <header style={{ maxWidth: 1200, margin: "0 auto 16px" }}>
        <p style={{ color: "#a3b9e0", margin: 0 }}>ÉTER · Prueba independiente</p>
        <h1 style={{ fontSize: "clamp(24px, 4vw, 36px)", margin: "6px 0" }}>Explorar el cielo</h1>
        <p style={{ margin: "6px 0 14px", maxWidth: 900 }}>
          Fondo infrarrojo AllWISE (WISE), servido por IRSA. Esta capa no es un mosaico SPHEREx.
          Arrastra para desplazarte y usa la rueda o los controles +/− para acercarte.
        </p>
        <nav aria-label="Controles de prueba" style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12 }}>
          <label htmlFor="sky-preset">Región inicial</label>
          <select id="sky-preset" value={viewIndex} onChange={(event) => setViewIndex(Number(event.target.value))}
            style={{ padding: "8px 12px", background: "#18243b", color: "#fff", border: "1px solid #8496b4", borderRadius: 6 }}>
            {views.map((item, index) => <option key={item.name} value={index}>{item.name}</option>)}
          </select>
          <button type="button" onClick={() => setRevision((value) => value + 1)}
            style={{ padding: "8px 12px", cursor: "pointer" }}>Reiniciar visor</button>
          <button type="button" onClick={() => setVisible((value) => !value)}
            style={{ padding: "8px 12px", cursor: "pointer" }}>{visible ? "Desmontar visor" : "Montar visor"}</button>
        </nav>
      </header>
      <section aria-label="Mapa del cielo" style={{ height: "70dvh", minHeight: 360, maxWidth: 1200, margin: "0 auto", border: "1px solid #35445f", borderRadius: 12, overflow: "hidden" }}>
        {visible ? (
          <AladinBackground key={revision} position={view.position} fovDeg={view.fovDeg}
            surveyUrl={ALLWISE_HIPS_URL} title="AllWISE: mapa infrarrojo del cielo" />
        ) : <p style={{ padding: 24 }}>Visor desmontado. Pulsa Montar visor para volver a cargarlo.</p>}
      </section>
      <footer style={{ maxWidth: 1200, margin: "12px auto 0", color: "#bcc9df", fontSize: 14 }}>
        WISE · NASA/JPL-Caltech/UCLA · HiPS CDS · Servicio IRSA · Visualización Aladin Lite.
        <br />Solo navegación y visualización. La detección de movimiento se conectará después.
      </footer>
    </main>
  );
}
