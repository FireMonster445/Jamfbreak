import { useEffect } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { AboutInfo, ThemeName } from "../types";
import { cn } from "../lib/utils";
import { IconButton } from "./IconButton";
import { CloseIcon } from "./icons";

const APPLE_EASE = [0.32, 0.72, 0, 1] as const;

const THEMES: Array<{
  id: ThemeName;
  name: string;
  desc: string;
  sample: string;
}> = [
  { id: "light", name: "Light", desc: "Clean daylight", sample: "#f5f5f5" },
  { id: "dark", name: "Dark", desc: "Default charcoal", sample: "#0a0a0a" },
  {
    id: "hacker",
    name: "Hacker",
    desc: "Terminal mode, for fun",
    sample: "#000000",
  },
];

function ThemeTile({
  theme,
  active,
  onPick,
}: {
  theme: (typeof THEMES)[number];
  active: boolean;
  onPick: () => void;
}) {
  return (
    <motion.button
      type="button"
      onClick={onPick}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.95 }}
      transition={{ type: "spring", stiffness: 420, damping: 26 }}
      className={cn(
        "flex-1 rounded-xl p-3 text-left outline-none transition-colors",
        active
          ? "bg-panel-2 ring-1 ring-ink/30"
          : "bg-panel hover:bg-panel-2",
        "focus-visible:ring-2 focus-visible:ring-neutral-500",
      )}
    >
      <div
        className="mb-2 h-10 w-full rounded-lg"
        style={{ background: theme.sample }}
      />
      <div className={cn("text-sm font-medium", active ? "text-ink" : "text-ink")}>
        {theme.name}
      </div>
      <div className="text-ink-faint mt-0.5 text-[11px]">{theme.desc}</div>
    </motion.button>
  );
}

function AboutRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="text-ink-dim shrink-0 text-[13px]">{label}</span>
      <span
        title={value}
        className="text-ink truncate font-mono text-[12.5px] text-right"
      >
        {value}
      </span>
    </div>
  );
}

/** Settings modal: blurred backdrop, theme picker, about/version details. */
export function SettingsDialog({
  open,
  onClose,
  theme,
  onThemeChange,
  about,
}: {
  open: boolean;
  onClose: () => void;
  theme: ThemeName;
  onThemeChange: (t: ThemeName) => void;
  about: AboutInfo | null;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const donors = about?.donors ?? {};

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: APPLE_EASE }}
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          style={{ background: "rgba(0,0,0,0.45)", backdropFilter: "blur(10px)" }}
          onClick={onClose}
        >
          <motion.div
            key="panel"
            initial={{ opacity: 0, scale: 0.94, y: 14 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 14 }}
            transition={{ duration: 0.35, ease: APPLE_EASE }}
            className="bg-panel w-full max-w-[430px] rounded-2xl p-5 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-ink text-lg font-semibold">Settings</h2>
              <div className="flex items-center gap-2">
                <span className="bg-panel-2 text-ink-dim rounded-md px-2 py-0.5 font-mono text-[11px]">
                  v{about?.app_version ?? "—"}
                </span>
                <IconButton label="Close settings" onClick={onClose}>
                  <CloseIcon className="h-4 w-4" />
                </IconButton>
              </div>
            </div>

            <div className="text-ink-dim mb-2 text-[11px] font-medium tracking-wide uppercase">
              Theme
            </div>
            <div className="mb-5 flex gap-2.5">
              {THEMES.map((t) => (
                <ThemeTile
                  key={t.id}
                  theme={t}
                  active={theme === t.id}
                  onPick={() => onThemeChange(t.id)}
                />
              ))}
            </div>

            <div className="text-ink-dim mb-1 text-[11px] font-medium tracking-wide uppercase">
              About
            </div>
            <div className="divide-line/40 rounded-xl bg-panel-2/40 px-3.5 py-2">
              <AboutRow label="Version" value={about?.app_version ?? "—"} />
              <AboutRow
                label="Distribution"
                value={about?.frozen ? "Portable EXE" : "Run from source"}
              />
              <AboutRow label="Engine" value={about?.webview_version ?? "—"} />
              <AboutRow label="Python" value={about?.python_version ?? "—"} />
              <AboutRow label="Platform" value={about?.platform ?? "—"} />
              <AboutRow
                label="Device binaries"
                value={about?.bin_present ? "detected" : "not found"}
              />
              <AboutRow
                label="Legacy donor"
                value={donors.legacy ? "present" : "missing"}
              />
              <AboutRow
                label="iOS 26 iPad donor"
                value={donors["ios26-ipad"] ? "present" : "missing"}
              />
              <AboutRow
                label="iOS 26 iPhone donor"
                value={donors["ios26-iphone"] ? "present" : "missing"}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
