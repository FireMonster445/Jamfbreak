import type { ReactNode } from "react";
import type { HTMLMotionProps } from "motion/react";
import { motion } from "motion/react";
import { cn } from "../lib/utils";

/**
 * Small square icon button used in the header/footer/console chrome.
 * Hover: scale + color lift. Click: quick press-down.
 */
export function IconButton({
  children,
  className,
  label,
  ...props
}: HTMLMotionProps<"button"> & { children: ReactNode; label: string }) {
  return (
    <motion.button
      type="button"
      aria-label={label}
      title={label}
      initial={false}
      whileHover={{ scale: 1.14 }}
      whileTap={{ scale: 0.88 }}
      transition={{ type: "spring", stiffness: 500, damping: 24 }}
      className={cn(
        "text-ink-faint hover:text-ink inline-flex cursor-pointer items-center justify-center",
        "rounded-lg p-1.5 outline-none transition-colors",
        "focus-visible:ring-2 focus-visible:ring-neutral-500",
        className,
      )}
      {...props}
    >
      {children}
    </motion.button>
  );
}
