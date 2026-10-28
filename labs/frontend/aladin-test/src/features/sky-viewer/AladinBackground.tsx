"use client";

import { useMemo } from "react";
import { ALLWISE_HIPS_URL, createAladinDocument, validateSkyOptions } from "./aladinDocument";
import type { AladinBackgroundProps } from "./types";

/**
 * El padre debe tener altura explícita. No depende de MUI ni de SpectralViewer.
 * Cambiar posición/FOV/capa reinicia la vista; un render con iguales valores no.
 * React retira el iframe al desmontar, junto con su documento y contexto WebGL.
 */
export default function AladinBackground({
  position = { raDeg: 0, decDeg: 0 },
  fovDeg = 360,
  surveyUrl = ALLWISE_HIPS_URL,
  className,
  style,
  title = "Mapa interactivo del cielo con Aladin Lite",
}: AladinBackgroundProps) {
  const { raDeg, decDeg } = position;
  const document = useMemo(() => {
    const options = { raDeg, decDeg, fovDeg, surveyUrl };
    const error = validateSkyOptions(options);
    return error ? { error, html: "" } : { error: null, html: createAladinDocument(options) };
  }, [raDeg, decDeg, fovDeg, surveyUrl]);

  if (document.error) {
    return <div role="alert" className={className} style={style}>{document.error}</div>;
  }

  return (
    <iframe
      title={title}
      className={className}
      srcDoc={document.html}
      style={{ display: "block", width: "100%", height: "100%", border: 0, ...style }}
    />
  );
}
