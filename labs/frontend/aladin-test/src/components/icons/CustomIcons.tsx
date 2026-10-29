import SvgIcon, { type SvgIconProps } from "@mui/material/SvgIcon";

/** Iconos que no existen en @mui/icons-material, dibujados como en el diseño de Figma. */

const line = {
  fill: "none",
  stroke: "currentColor",
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

/** Órbita: icono de «Fenómenos y cuerpos celestes». */
export function OrbitIcon(props: SvgIconProps) {
  return (
    <SvgIcon {...props} viewBox="0 0 24 24">
      <g {...line} strokeWidth={1.6}>
        <circle cx="11.5" cy="12.5" r="3" />
        <circle cx="18.5" cy="5.5" r="1.8" />
        <path d="M14.8 3.3A9.5 9.5 0 1 0 20.7 9.2" />
      </g>
    </SvgIcon>
  );
}

/** Cruz fina del centro de la imagen. */
export function CrosshairIcon(props: SvgIconProps) {
  return (
    <SvgIcon {...props} viewBox="0 0 24 24">
      <g {...line} strokeWidth={1}>
        <path d="M12 3v18M3 12h18" />
      </g>
    </SvgIcon>
  );
}
