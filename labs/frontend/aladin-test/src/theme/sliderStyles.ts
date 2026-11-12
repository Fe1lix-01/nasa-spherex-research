import { eter, selectedRing } from "./theme";

/**
 * Estilo "de luz" compartido por los sliders (panel de controles y línea de tiempo):
 * barra llena blanca con brillo, y perilla con el aro de luz de los botones.
 *
 * `p` va de 0 a 1 (posición del valor dentro de su rango): hacia la izquierda todo se ve más
 * tenue y hacia la derecha se intensifica.
 * `spin`: true = el aro gira solo (animación CSS); false = lo gira quien use este helper.
 */
export function glowSliderParts(p: number, spin: boolean) {
  const ring = selectedRing("0px", "50%", spin);

  return {
    "& .MuiSlider-rail": { opacity: 1, backgroundColor: eter.rail },

    // Barra llena: siempre blanca, con degradado y resplandor que crecen con el valor.
    "& .MuiSlider-track": {
      border: "none",
      height: 2,
      background: `linear-gradient(90deg, rgba(255,255,255,${0.2 + 0.4 * p}), rgba(255,255,255,${0.6 + 0.4 * p}))`,
      boxShadow: `0 0 ${2 + 8 * p}px rgba(255,255,255,${0.1 + 0.4 * p})`,
    },

    "& .MuiSlider-thumb": {
      ...ring,
      position: "absolute", // selectedRing pone "relative"; MUI necesita "absolute" para ubicar la perilla
      width: 16,
      height: 16,
      // Relleno opaco (para que la barra no se vea cruzando la perilla) en un gris-azulado que
      // se aclara con el valor. El aro, que va encima, conserva todo su contraste.
      backgroundColor: eter.panel,
      backgroundImage: `linear-gradient(rgba(170,190,230,${0.14 + 0.16 * p}), rgba(170,190,230,${0.14 + 0.16 * p}))`,
      boxShadow: `0 0 0 4px rgba(255,255,255,${0.03 + 0.1 * p}), 0 0 ${4 + 14 * p}px rgba(255,255,255,${0.08 + 0.4 * p})`,
      // MUI ya usa este pseudo-elemento para su sombra: se reutiliza para el aro de luz.
      "&::before": {
        ...ring["&::before"],
        width: "100%",
        height: "100%",
        boxSizing: "border-box",
        boxShadow: "none",
        opacity: 0.55 + 0.45 * p, // más tenue hacia la izquierda, más intenso hacia la derecha
      },
      "&:hover, &.Mui-focusVisible, &.Mui-active": {
        boxShadow: `0 0 0 7px rgba(255,255,255,${0.06 + 0.12 * p}), 0 0 ${6 + 16 * p}px rgba(255,255,255,${0.15 + 0.45 * p})`,
      },
    },
  } as const;
}