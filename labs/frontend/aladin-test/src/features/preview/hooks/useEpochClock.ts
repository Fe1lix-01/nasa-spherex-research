"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Pausa al llegar a la última época antes de reiniciar el ciclo, en milisegundos. */
const HOLD_MS = 900;

/**
 * Reloj de la animación. `t` va de 0 a (count - 1): cada unidad es una época, y los
 * decimales son el tiempo entre dos épocas (t = 1.5 → a medio camino entre la 2 y la 3).
 *
 * Al llegar al final espera un momento y vuelve a empezar, como un video en bucle.
 */
export function useEpochClock(count: number, secondsPerEpoch = 3) {
  const last = Math.max(count - 1, 0);
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const tRef = useRef(0); // valor actual, para leerlo dentro del ciclo sin reiniciarlo

  const seek = useCallback(
    (value: number) => {
      const v = Math.min(Math.max(value, 0), last);
      tRef.current = v;
      setT(v);
    },
    [last],
  );

  useEffect(() => {
    if (!playing || last === 0) return;
    let raf = 0;
    let prev = performance.now();
    let holdUntil = 0;

    const tick = (now: number) => {
      const dt = (now - prev) / 1000;
      prev = now;

      if (holdUntil > 0) {
        if (now >= holdUntil) {
          holdUntil = 0;
          seek(0);
        }
      } else {
        const next = tRef.current + (dt * speed) / secondsPerEpoch;
        if (next >= last) {
          seek(last);
          holdUntil = now + HOLD_MS;
        } else {
          seek(next);
        }
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, last, secondsPerEpoch, seek]);

  const play = useCallback(() => {
    if (tRef.current >= last) seek(0); // si ya terminó, empieza de nuevo
    setPlaying(true);
  }, [last, seek]);

  const pause = useCallback(() => setPlaying(false), []);
  const toggle = useCallback(() => (playing ? pause() : play()), [playing, pause, play]);

  return { t, playing, speed, setSpeed, play, pause, toggle, seek, last };
}
