import { useEffect, useState } from "react";
import { cn } from "../lib/utils";

/**
 * Command-line typewriter used in the hacker theme: text is typed out
 * character-by-character behind a block cursor, like a terminal echo.
 * Re-runs whenever `text` changes (new status etc.).
 */
export function HackerText({
  text,
  className,
  speedMs = 28,
}: {
  text: string;
  className?: string;
  speedMs?: number;
}) {
  const [shown, setShown] = useState("");

  useEffect(() => {
    setShown("");
    if (!text) return;
    let i = 0;
    const tick = () => {
      i += 1;
      setShown(text.slice(0, i));
      if (i < text.length) {
        timer = window.setTimeout(tick, speedMs + Math.random() * 40);
      }
    };
    let timer = window.setTimeout(tick, speedMs);
    return () => window.clearTimeout(timer);
  }, [text, speedMs]);

  return (
    <span className={cn("tabular-nums", className)}>
      {shown}
      <span className="bg-ink text-canvas ml-0.5 inline-block h-[1em] w-[0.55em] translate-y-[0.15em] animate-pulse" />
    </span>
  );
}
