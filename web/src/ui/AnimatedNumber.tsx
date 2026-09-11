import { useEffect, useRef } from "react";
import { animate, useMotionValue, useReducedMotion } from "framer-motion";

interface Props {
  value: number;
  decimals?: number;
  className?: string;
}

/** Frontend.md §3.7 — on disease switch, "right-rail values count/
 * interpolate to their new numbers." Respects prefers-reduced-motion
 * (snaps instead of animating), per §3.3 rule 3 and §11.
 */
export default function AnimatedNumber({ value, decimals = 2, className }: Props) {
  const spanRef = useRef<HTMLSpanElement>(null);
  const motionVal = useMotionValue(value);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    if (!spanRef.current) return;

    if (prefersReducedMotion) {
      spanRef.current.textContent = value.toFixed(decimals);
      motionVal.set(value);
      return;
    }

    const controls = animate(motionVal, value, {
      duration: 0.45,
      ease: "easeOut",
      onUpdate: (v) => {
        if (spanRef.current) spanRef.current.textContent = v.toFixed(decimals);
      },
    });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <span ref={spanRef} className={className}>
      {value.toFixed(decimals)}
    </span>
  );
}
