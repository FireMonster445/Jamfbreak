import type { HTMLMotionProps } from "motion/react";
import { Button as AnimateButton } from "@animate-ui/react/primitives/buttons/button";
import { cn } from "../lib/utils";

/**
 * Jamfbreak action buttons, built on the Animate UI Button primitive.
 * Hover: background darkens. Click: quick size-down (whileTap spring).
 */
type Variant = "primary" | "secondary";

export function ActionButton({
  variant = "primary",
  className,
  ...props
}: HTMLMotionProps<"button"> & { variant?: Variant }) {
  return (
    <AnimateButton
      initial={false}
      whileTap={{ scale: 0.94 }}
      whileHover={{ scale: 1.03 }}
      transition={{ type: "spring", stiffness: 420, damping: 26 }}
      className={cn(
        "inline-flex h-10 cursor-pointer items-center justify-center rounded-lg",
        "px-8 text-[15px] font-medium outline-none",
        "transition-colors duration-200",
        "focus-visible:ring-2 focus-visible:ring-neutral-500 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas",
        "disabled:pointer-events-none disabled:opacity-40",
        variant === "primary" &&
          "bg-accent-bg text-accent-fg hover:brightness-90",
        variant === "secondary" &&
          "bg-accent-bg-dark text-accent-fg-dark hover:brightness-75",
        className,
      )}
      {...props}
    />
  );
}
