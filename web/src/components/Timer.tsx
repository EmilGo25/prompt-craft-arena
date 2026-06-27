import { useEffect, useRef, useState } from "react";
import { useTranslation } from "../i18n";

const URGENT_THRESHOLD = 5; // seconds

/**
 * Smooth, skew-corrected countdown. Counts down with requestAnimationFrame
 * against the server-provided deadline (already corrected for clock offset in
 * the store), so it stays accurate between the 1s server ticks. Turns red and
 * pulses in the final seconds — an honest urgency cue, not an anxiety trick.
 */
export function Timer({ deadlineLocalMs }: { deadlineLocalMs: number | null }) {
  const { t } = useTranslation();
  const [secondsLeft, setSecondsLeft] = useState<number>(0);
  const raf = useRef<number>(0);

  useEffect(() => {
    if (deadlineLocalMs == null) return;
    const tick = () => {
      const remaining = Math.max(0, (deadlineLocalMs - Date.now()) / 1000);
      setSecondsLeft(remaining);
      if (remaining > 0) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [deadlineLocalMs]);

  const whole = Math.ceil(secondsLeft);
  const urgent = secondsLeft <= URGENT_THRESHOLD;

  return (
    <div className={`timer ${urgent ? "timer-urgent" : ""}`} role="timer" aria-live="off">
      <span className="timer-num">{whole}</span>
      <span className="timer-unit">{t("common.secondsUnit")}</span>
    </div>
  );
}
