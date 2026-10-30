import { Fragment, useEffect, useRef } from "react";
import { motion } from "motion/react";
import type { AboutInfo, AppState } from "../types";
import { cn } from "../lib/utils";
import { HackerText } from "./HackerText";

/*
 * HackerShell — the "hacker" theme renders the whole app as a single
 * command-line tool, like a plain CLI inside the terminal: one scrolling
 * console surface, prompt-prefixed output, no panels/boxes/borders.
 * Every interaction that exists in the normal theme is a clickable
 * inline command.
 */

const APPLE_EASE = [0.32, 0.72, 0, 1] as const;

const transition = { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const };
const variants = {
  hidden: { filter: "blur(8px)", transform: "translateY(20%)", opacity: 0 },
  visible: { filter: "blur(0px)", transform: "translateY(0%)", opacity: 1 },
};

const STATUS_LINE: Record<AppState["status"], string> = {
  searching: "scanning usb bus for ios device... not found",
  connected: "device handshake ok — target acquired",
  patching: "executing restore sequence... do not disconnect",
  success: "mdm profile removed. device unlocked.",
  error: "command aborted — see log below",
};

function CmdButton({
  label,
  onClick,
  disabled,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.92 }}
      transition={{ type: "spring", stiffness: 500, damping: 26 }}
      className={cn(
        "cursor-pointer outline-none transition-colors",
        "text-hk-accent border-hk-accent/60 border px-3 py-1 text-[13px] tracking-wide",
        "hover:text-hk-on-accent hover:bg-hk-accent",
        "disabled:pointer-events-none disabled:opacity-35",
        "focus-visible:ring-1 focus-visible:ring-hk-accent",
      )}
    >
      {label}
    </motion.button>
  );
}

/** One output line, blur-in per word, prefixed like terminal output. */
function OutLine({ kind, words }: { kind: string; words: string[] }) {
  const color =
    kind === "error"
      ? "text-hk-danger"
      : kind === "success"
        ? "text-hk-accent"
        : kind === "step"
          ? "text-hk-strong"
          : "text-hk-dim";
  return (
    <motion.div
      className={cn("mb-0.5 text-[13.5px] leading-6 break-words", color)}
    >
      {kind === "error" ? "[×] " : kind === "success" ? "[✓] " : "> "}
      <motion.span
        initial="hidden"
        animate="visible"
        transition={{ staggerChildren: 0.02 }}
      >
        {words.map((word, index) => (
          <Fragment key={index}>
            <motion.span
              className="inline-block"
              transition={transition}
              variants={variants}
            >
              {word}
            </motion.span>
            {index < words.length - 1 && " "}
          </Fragment>
        ))}
      </motion.span>
    </motion.div>
  );
}

export function HackerShell({
  state,
  about,
  onBypass,
  onRefresh,
  onOpenSettings,
  onOpenGithub,
}: {
  state: AppState;
  about: AboutInfo | null;
  onBypass: () => void;
  onRefresh: () => void;
  onOpenSettings: () => void;
  onOpenGithub: () => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const isPatching =
    state.status === "patching" || state.status === "success";
  const noDevice = state.device === null;

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.logs.length]);

  const DEVICE_ROWS: Array<[string, string]> = state.device
    ? [
        ["model", String(state.device.product_type ?? "—")],
        ["name", String(state.device.name ?? "—")],
        ["ios", String(state.device.product_version ?? "—")],
        ["build", String(state.device.build_version ?? "—")],
        ["serial", String(state.device.serial ?? "—")],
        ["udid", String(state.device.udid ?? "—")],
        ["imei", String(state.device.imei ?? "—")],
        ["activation", String(state.device.activation_state ?? "—")],
      ]
    : [];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, ease: APPLE_EASE }}
      className="flex h-full w-full flex-col overflow-hidden"
    >
      {/* Title bar: plain text, like a console prompt header */}
      <div className="flex items-baseline justify-between px-6 pt-4 pb-2">
        <div className="text-hk-strong text-[14px] tracking-wide">
          <HackerText
            text={`jamfbreak v${about?.app_version ?? "1.0.7"} — mdm bypass cli`}
            speedMs={14}
          />
        </div>
        <div className="flex items-center gap-2">
          <CmdButton label="settings" onClick={onOpenSettings} />
          <CmdButton label="github" onClick={onOpenGithub} />
        </div>
      </div>

      {/* The single console surface */}
      <div className="thin-scroll min-h-0 flex-1 overflow-y-auto px-6 pb-2">
        <div ref={scroller} className="h-full">
          <OutLine
            kind="step"
            words={[
              `C:\\jamfbreak> connect --wait --target ios-device`,
            ]}
          />
          <OutLine kind="info" words={[STATUS_LINE[state.status]]} />

          {/* Device identity as flat key: value lines */}
          {DEVICE_ROWS.map(([key, value]) => (
            <motion.div
              key={key}
              initial={{ opacity: 0, filter: "blur(6px)" }}
              animate={{ opacity: 1, filter: "blur(0px)" }}
              transition={{ duration: 0.45, ease: APPLE_EASE }}
              className="text-[13.5px] leading-6 break-all"
            >
              <span className="text-hk-faint">{`  ${key.padEnd(12, " ")}`}</span>
              <span className="text-hk-dim">= </span>
              <span className="text-hk-strong" title={value}>
                {value}
              </span>
            </motion.div>
          ))}
          {!state.device && (
            <div className="text-hk-faint mb-1 text-[13.5px] leading-6">
              {"  (no device identity yet — waiting for connection)"}
            </div>
          )}

          {/* Log output, terminal style */}
          <div className="mt-3 border-t border-hk-line pt-2" />
          {state.logs.map((entry, index) => (
            <OutLine
              key={index}
              kind={entry.kind}
              words={String(entry.text ?? "").split(" ")}
            />
          ))}

          {/* Inline command buttons */}
          <div className="mt-3 flex items-center gap-3">
            <CmdButton
              label="run bypass"
              onClick={onBypass}
              disabled={isPatching || noDevice}
            />
            <CmdButton
              label="rescan device"
              onClick={onRefresh}
              disabled={isPatching}
            />
          </div>

          {/* Cursor prompt at the bottom, matching terminal consoles */}
          <div className="mt-2 text-[13.5px] leading-6">
            <span className="text-hk-strong">C:\jamfbreak&gt; </span>
            <span className="bg-hk-accent inline-block h-[1em] w-[0.55em] translate-y-[0.12em] animate-pulse" />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
