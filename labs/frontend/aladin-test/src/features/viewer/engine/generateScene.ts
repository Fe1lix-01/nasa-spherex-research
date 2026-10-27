import { H, N, W } from "../constants";
import type { Layers } from "../types";
import { fbm, rng, sstep } from "./noise";

/* ---------- API ---------- */

export function createLayers(): Layers {
  return {
    v: new Float32Array(N),
    neb: new Float32Array(N),
    ir: new Float32Array(N),
    th: new Float32Array(N),
    ice: new Float32Array(N),
  };
}

/** Rellena las capas con una escena simulada: nebulosa, polvo, galaxia, estrellas y protoestrellas. */
export function generateScene(L: Layers): void {
  const dustMap = new Float32Array(N);
  const cs = Math.cos(-0.5);
  const sn = Math.sin(-0.5);

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      const u = x / H;
      const w = y / H;

      const dn = fbm(u * 3.2 + 10, w * 3.2, 3);
      const dust = sstep(0.48, 0.72, dn);
      const core = sstep(0.62, 0.8, dn);
      const neb =
        sstep(0.4, 0.8, fbm(u * 2.4 + 40, w * 2.4 + 7, 9)) *
        (0.35 + 0.65 * sstep(0.3, 0.6, fbm(u * 1.1, w * 1.1, 21))) *
        (1 - dust * 0.8);

      const dx = u - 1.35;
      const dy = w - 0.3;
      const xr = dx * cs + dy * sn;
      const yr = -dx * sn + dy * cs;
      const r = Math.hypot(xr / 0.28, yr / 0.075);
      const lane = 1 - 0.6 * Math.exp(-Math.pow(yr / 0.008, 2)) * sstep(1.6, 0.4, r);
      const gal =
        (Math.exp(-r * 1.6) * 0.7 + Math.exp(-r * r * 6)) *
        lane *
        (0.8 + 0.4 * fbm(u * 8, w * 8, 30));
      const warm = fbm(u * 2 + 70, w * 2, 50);

      dustMap[i] = dust;
      L.neb[i] = neb * 0.9;
      L.v[i] = (neb * 0.35 + gal * 0.9) * (1 - dust * 0.85) + 0.02;
      L.ir[i] = dust * (0.35 + 0.6 * core) + gal * 0.8 * (1 - dust * 0.2) + neb * 0.15;
      L.th[i] =
        Math.pow(dust, 1.5) * (0.25 + 0.75 * core) * (0.6 + 0.4 * warm) +
        Math.exp(-r * r * 6) * 0.5;
      L.ice[i] = core * sstep(0.2, 0.9, dust) * (0.7 + 0.3 * fbm(u * 6, w * 6, 60));
    }
  }

  const rand = rng(7);

  /** Suma una estrella (mancha gaussiana) en cada banda. El polvo la atenúa. */
  const blob = (cx: number, cy: number, s: number, bv: number, bi: number, bt: number) => {
    const R = Math.ceil(s * 3);
    for (let yy = -R; yy <= R; yy++) {
      for (let xx = -R; xx <= R; xx++) {
        const px = cx + xx;
        const py = cy + yy;
        if (px < 0 || py < 0 || px >= W || py >= H) continue;
        const g = Math.exp(-(xx * xx + yy * yy) / (2 * s * s));
        const i = py * W + px;
        const d = dustMap[i];
        L.v[i] += bv * g * (1 - d * 0.9);
        L.ir[i] += bi * g * (1 - d * 0.25);
        L.th[i] += bt * g;
      }
    }
  };

  for (let k = 0; k < 520; k++) {
    const x = (rand() * W) | 0;
    const y = (rand() * H) | 0;
    const b = Math.pow(rand(), 3) * 1.3 + 0.05;
    const red = 0.3 + rand() * 0.9;
    const s = (0.8 + rand() * 1.1) * (H / 540);
    blob(x, y, s, b, b * red, b * 0.08);
  }

  // Protoestrellas: casi invisibles en luz visible, brillan en IR y térmico.
  let placed = 0;
  let tries = 0;
  while (placed < 14 && tries++ < 4000) {
    const x = (rand() * W) | 0;
    const y = (rand() * H) | 0;
    if (dustMap[y * W + x] > 0.7) {
      blob(x, y, 2.2 * (H / 540), 0, 0.9, 1.1);
      placed++;
    }
  }
}