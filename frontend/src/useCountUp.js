// useCountUp.js — animates a number from 0 to `target` over `duration` ms.
// Used for the score, probability, etc. so figures count up rather than snapping.
// Respects prefers-reduced-motion: if the user wants less motion, it jumps
// straight to the final value.

import { useEffect, useRef, useState } from "react";

export function useCountUp(target, duration = 900, decimals = 0) {
  const [value, setValue] = useState(0);
  const startRef = useRef(null);
  const fromRef = useRef(0);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setValue(target); return; }

    const from = fromRef.current;
    startRef.current = null;
    let raf;

    // easeOutCubic: fast start, gentle settle — the "premium" easing.
    const ease = (t) => 1 - Math.pow(1 - t, 3);

    function tick(now) {
      if (startRef.current === null) startRef.current = now;
      const elapsed = now - startRef.current;
      const t = Math.min(elapsed / duration, 1);
      const next = from + (target - from) * ease(t);
      setValue(next);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return decimals > 0 ? Number(value.toFixed(decimals)) : Math.round(value);
}
