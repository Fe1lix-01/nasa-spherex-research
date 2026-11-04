import type { CSSProperties } from "react";

/** Coordenadas ecuatoriales ICRS, siempre en grados decimales. */
export interface SkyPosition {
  raDeg: number;
  decDeg: number;
}

export interface AladinBackgroundProps {
  position?: SkyPosition;
  /** Campo de visión horizontal en grados. Menor valor = más acercamiento. */
  fovDeg?: number;
  /** URL raíz de un HiPS, NO de un FITS, PNG ni del explorador de IRSA. */
  surveyUrl?: string;
  className?: string;
  style?: CSSProperties;
  title?: string;
}

export interface SkyDocumentOptions {
  raDeg: number;
  decDeg: number;
  fovDeg: number;
  surveyUrl: string;
}
