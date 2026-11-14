export default function SciencePage() {
  return (
    <main style={{ padding: "2rem", maxWidth: 1200, margin: "auto" }}>
      <h1>Vista exploratoria de M101</h1>
      <p>Canal 63, cobertura y máscara de calidad del experimento de SPHEREx.</p>
      <p>Esta figura es una vista exploratoria y no representa una comparación temporal.</p>
      {/* La imagen se solicita al backend a través del proxy local de Next.js. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/api/science/m101" alt="M101, canal 63, cobertura y máscara" style={{ width: "100%", height: "auto" }} />
    </main>
  );
}
