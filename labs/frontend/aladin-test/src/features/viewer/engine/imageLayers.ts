import { H, N, W } from "../constants";
import type { Layers } from "../types";

/**
 * Convierte una imagen (RGB) en capas aproximadas.
 * Es solo una aproximación visual: con datos reales cada banda sería su propia imagen.
 */
function imageToLayers(im: HTMLImageElement, L: Layers): void {
  const c = document.createElement("canvas");
  c.width = W;
  c.height = H;
  const cx = c.getContext("2d");
  if (!cx) throw new Error("No se pudo crear el lienzo");
  // recorte tipo "cover" para llenar el lienzo
  const s = Math.max(W / im.width, H / im.height);
  const dw = im.width * s;
  const dh = im.height * s;
  cx.drawImage(im, (W - dw) / 2, (H - dh) / 2, dw, dh);
  const px = cx.getImageData(0, 0, W, H).data;
  for (let i = 0, p = 0; i < N; i++, p += 4) {
    const r = px[p] / 255;
    const g = px[p + 1] / 255;
    const b = px[p + 2] / 255;
    const l = 0.299 * r + 0.587 * g + 0.114 * b;
    L.v[i] = l;
    L.neb[i] = 0;
    L.ir[i] = Math.pow(r, 1.2) * 0.9 + l * 0.1;
    L.th[i] = Math.pow(r * 0.7 + l * 0.3, 2);
    L.ice[i] = Math.max(0, b - r) * 1.6;
  }
}

/** Carga una imagen desde una URL (por ejemplo /escena-demo.jpg en la carpeta public). */
export function loadUrlIntoLayers(url: string, L: Layers): Promise<void> {
  return new Promise((resolve, reject) => {
    const im = new Image();
    im.onload = () => {
      try {
        imageToLayers(im, L);
        resolve();
      } catch (err) {
        reject(err);
      }
    };
    im.onerror = () => reject(new Error(`No se pudo cargar ${url}`));
    im.src = url;
  });
}

/** Carga una imagen elegida por la persona (botón «Subir imagen»). */
export function loadImageIntoLayers(file: File, L: Layers): Promise<void> {
  const url = URL.createObjectURL(file);
  return loadUrlIntoLayers(url, L).finally(() => URL.revokeObjectURL(url));
}