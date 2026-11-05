import type { RefObject } from "react";
import { H, W } from "../constants";

type Props = {
  canvasRef: RefObject<HTMLCanvasElement | null>;
};

/** Fondo con filtros: dibuja la escena en un canvas que cubre toda la pantalla. */
export default function ViewerCanvas({ canvasRef }: Props) {
  return (
    <canvas
      ref={canvasRef}
      width={W}
      height={H}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }}
    />
  );
}