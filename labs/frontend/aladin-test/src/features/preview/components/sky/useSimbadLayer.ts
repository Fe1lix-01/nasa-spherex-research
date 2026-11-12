"use client";

/**
 * Capa SIMBAD sobre Aladin: marcas de objetos conocidos, aviso al pasar el cursor y objeto
 * seleccionado al hacer clic.
 *
 * Por qué es un hook aparte: SkyStage.tsx es de Alex. Toda la lógica vive aquí y SkyStage solo
 * le pasa la vista de Aladin, así que el cambio en su archivo es de unas pocas líneas.
 */

import { useEffect, useRef, useState } from "react";
import { findObjectsInField, MAX_FOV_FOR_LAYER, type SimbadObject } from "../../model/simbad";

/* Tipos mínimos de lo que usamos de Aladin: así no hay que ampliar los de SkyStage. */
type AladinCatalog = { addSources(sources: unknown[]): void; removeAll(): void; show(): void; hide(): void };
export type SimbadAladinApi = {
  catalog(options: Record<string, unknown>): AladinCatalog;
  source(ra: number, dec: number, data: unknown): unknown;
};
export type SimbadAladinView = {
  addCatalog(catalog: AladinCatalog): void;
  getRaDec(): [number, number];
  getFov(): [number, number];
  on(event: string, callback: (...args: unknown[]) => void): void;
};

export type SimbadLayerStatus = "off" | "wide" | "loading" | "ready" | "error";

/** Mientras estemos probando, imprime en consola lo que manda Aladin en cada evento. */
const DEBUG = true;
/** Espera tras mover o hacer zoom antes de consultar, para no pedir nada a mitad de un arrastre. */
const DEBOUNCE_MS = 400;

/** Distancia angular entre dos puntos del cielo, en grados. */
function separationDeg(ra1: number, dec1: number, ra2: number, dec2: number) {
  const rad = Math.PI / 180;
  const a = Math.sin(((dec2 - dec1) * rad) / 2) ** 2;
  const b = Math.cos(dec1 * rad) * Math.cos(dec2 * rad) * Math.sin(((ra2 - ra1) * rad) / 2) ** 2;
  return (2 * Math.asin(Math.sqrt(a + b))) / rad;
}

/** Aladin entrega el objeto como una "source"; nuestros datos van en `.data`. */
function asSimbadObject(source: unknown): SimbadObject | null {
  const data = (source as { data?: Partial<SimbadObject> } | null)?.data;
  return data && typeof data.oid === "number" ? (data as SimbadObject) : null;
}

type Args = {
  A: SimbadAladinApi | null;
  view: SimbadAladinView | null;
  /** Contenedor del visor: de ahí se toma la posición del cursor para el aviso. */
  host: HTMLElement | null;
  enabled: boolean;
};

export function useSimbadLayer({ A, view, host, enabled }: Args) {
  const [status, setStatus] = useState<SimbadLayerStatus>("off");
  const [hovered, setHovered] = useState<SimbadObject | null>(null);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const [selected, setSelected] = useState<SimbadObject | null>(null);

  // `enabled` se lee desde los eventos de Aladin (que se registran una sola vez), por eso va en un ref.
  const enabledRef = useRef(enabled);
  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const catalogRef = useRef<AladinCatalog | null>(null);
  const refresh = useRef<() => void>(() => {});

  /* Registro único: catálogo, eventos y consulta. */
  useEffect(() => {
    if (!A || !view) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;
    let last: { ra: number; dec: number; radius: number } | null = null;

    const catalog = A.catalog({ name: "SIMBAD", sourceSize: 14, shape: "circle", color: "rgba(255,255,255,0.9)", hoverColor: "#ffd24c" });
    view.addCatalog(catalog);
    catalogRef.current = catalog;

    const query = async () => {
      if (!active) return;
      if (!enabledRef.current) {
        catalog.removeAll();
        last = null;
        setStatus("off");
        return;
      }
      const [ra, dec] = view.getRaDec();
      const fov = Math.max(...view.getFov());
      if (fov > MAX_FOV_FOR_LAYER) {
        catalog.removeAll();
        last = null;
        setStatus("wide");
        return;
      }
      const radius = fov / 2;
      // Si la vista nueva cabe dentro de lo ya consultado, no se vuelve a pedir nada.
      if (last && separationDeg(ra, dec, last.ra, last.dec) + radius <= last.radius) {
        setStatus("ready");
        return;
      }
      controller?.abort(); // una consulta más nueva cancela la anterior
      controller = new AbortController();
      setStatus("loading");
      try {
        // Se pide un poco más que lo visible para que mover un poco el cielo no obligue a repetir.
        const fetchRadius = radius * 1.4;
        const objects = await findObjectsInField(ra, dec, fetchRadius, controller.signal);
        if (!active) return;
        catalog.removeAll();
        catalog.addSources(objects.map((o) => A.source(o.ra, o.dec, o)));
        last = { ra, dec, radius: fetchRadius };
        setStatus("ready");
      } catch {
        if (active && !controller?.signal.aborted) setStatus("error");
      }
    };

    const schedule = () => {
      clearTimeout(timer);
      timer = setTimeout(query, DEBOUNCE_MS);
    };
    refresh.current = schedule;

    view.on("positionChanged", schedule);
    view.on("zoomChanged", schedule);

    view.on("objectHovered", (source) => {
      if (DEBUG) console.log("[SIMBAD] objectHovered", source);
      setHovered(asSimbadObject(source));
    });
    view.on("objectHoveredStop", () => setHovered(null));
    view.on("objectClicked", (source) => {
      if (DEBUG) console.log("[SIMBAD] objectClicked", source);
      // Clic en el cielo vacío: llega null y se cierra la tarjeta.
      setSelected(asSimbadObject(source));
    });

    schedule();

    return () => {
      active = false;
      clearTimeout(timer);
      controller?.abort();
      catalog.removeAll();
      catalog.hide();
    };
  }, [A, view]);

  /* Al encender o apagar la capa, se consulta o se limpia. */
  useEffect(() => {
    refresh.current();
    if (!enabled) {
      setHovered(null);
      setSelected(null);
    }
  }, [enabled]);

  /* Posición del cursor dentro del visor, para colocar el aviso junto a la marca. */
  useEffect(() => {
    if (!host) return;
    const onMove = (e: PointerEvent) => {
      const r = host.getBoundingClientRect();
      setPointer({ x: e.clientX - r.left, y: e.clientY - r.top });
    };
    host.addEventListener("pointermove", onMove);
    return () => host.removeEventListener("pointermove", onMove);
  }, [host]);

  return { status, hovered, pointer, selected, clearSelected: () => setSelected(null) };
}