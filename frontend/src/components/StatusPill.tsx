import { motion } from "motion/react";
import type { Status } from "../types";
import { cn } from "../lib/utils";

const APPLE_EASE = [0.32, 0.72, 0, 1] as const;

const LABEL: Record<Status, string> = {
  searching: "Searching",
  connected: "Device Connected",
  patching: "Bypassing",
  success: "Bypass OK",
  error: "Error",
};

/** Header status pill: dark plate, animated dot (pulse while searching). */
export function StatusPill({ status }: { status: Status }) {
  const connected = status === "connected";
  const busy = status === "patching";
  const failed = status === "error";

  return (
    <div
      className={cn(
        "bg-panel inline-flex h-9 items-center gap-2.5 rounded-lg px-3",
        "hacker-flicker",
      )}
    >
      <span className="text-ink text-sm font-medium whitespace-nowrap">
        {LABEL[status]}
      </span>
      <span className="relative flex h-2.5 w-2.5 items-center justify-center">
        {busy && (
          <motion.span
            className="bg-dot-ok absolute inset-0 rounded-full opacity-50"
            animate={{ scale: [1, 2.2], opacity: [0.5, 0] }}
            transition={{ duration: 1, repeat: Infinity, ease: "easeOut" }}
          />
        )}
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: connected || busy || failed ? 1 : 0.5 }}
          transition={{ duration: 0.3, ease: APPLE_EASE }}
          className={cn(
            "bg-dot-ok rounded-full",
            connected || busy || failed ? "opacity-100" : "opacity-25",
          )}
          style={{ width: 10, height: 10 }}
        />
      </span>
    </div>
  );
}

