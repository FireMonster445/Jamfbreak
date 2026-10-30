import { Fragment, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import type { LogEntry } from "../types";
import { cn } from "../lib/utils";
import { IconButton } from "./IconButton";
import { CopyIcon, RefreshIcon } from "./icons";

/*
 * BlurReveal — per-word blur-in, from the supplied spec component:
 *   hidden:  blur(10px), translateY(20%), opacity 0
 *   visible: blur(0), translateY(0), opacity 1
 *   duration 1, ease [.25,.1,.25,1], children staggered 0.04s
 */
const transition = { duration: 1, ease: [0.25, 0.1, 0.25, 1] as const };
const variants = {
  hidden: {
    filter: "blur(10px)",
    transform: "translateY(20%)",
    opacity: 0,
  },
  visible: {
    filter: "blur(0px)",
    transform: "translateY(0%)",
    opacity: 1,
  },
};

const KIND_CLASS: Record<string, string> = {
  info: "text-ink-dim",
  success: "text-emerald-400",
  error: "text-rose-400",
  step: "text-ink",
};

function timestamp() {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/** One console line, revealed word-by-word with the blur effect. */
function LogLine({ entry }: { entry: LogEntry }) {
  const words = String(entry.text ?? "").split(" ");
  return (
    <motion.div
      className="mb-1.5 flex items-start gap-2.5 pl-4 font-mono text-[13px] leading-6"
      // Container hides children, each word staggers in.
    >
      <span className="text-ink-faint mt-0.5 shrink-0 text-[12px]">
        {timestamp()}
      </span>
      {entry.tag ? (
        <span
          className={cn(
            "bg-panel-2 text-ink-dim mt-0.5 shrink-0 rounded px-1.5 text-[11px]",
            KIND_CLASS[entry.kind] ?? KIND_CLASS.info,
          )}
        >
          {String(entry.tag ?? "")}
        </span>
      ) : null}
      <motion.span
        initial="hidden"
        animate="visible"
        transition={{ staggerChildren: 0.04 }}
        className={cn(
          "min-w-0 flex-wrap break-words",
          KIND_CLASS[entry.kind] ?? KIND_CLASS.info,
        )}
      >
        {words.map((word, index) => (
          <Fragment key={index}>
            <motion.span className="inline-block" transition={transition} variants={variants}>
              {word}
            </motion.span>
            {index < words.length - 1 && " "}
          </Fragment>
        ))}
      </motion.span>
    </motion.div>
  );
}

/** The console panel: header row (copy + refresh) and scroll-locked lines. */
export function Console({
  logs,
  onRefresh,
}: {
  logs: LogEntry[];
  onRefresh: () => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logs.length]);

  async function copyAll() {
    try {
      const text = logs
        .map((e) => `[${timestamp()}] ${e.tag ? `[${e.tag}] ` : ""}${e.text}`)
        .join("\n");
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      // clipboard can be blocked outside pywebview; ignore
    }
  }

  return (
    <section className="bg-panel flex h-full min-h-0 flex-col overflow-hidden rounded-2xl">
      {/* Header row wraps around the console output content, like the redesign */}
      <div className="flex items-center justify-between px-5 py-3.5">
        <h2 className="text-ink text-[17px] font-semibold">Console</h2>
        <div className="flex items-center gap-1">
          <IconButton label={copied ? "Copied" : "Copy console"} onClick={copyAll}>
            <CopyIcon className="h-[18px] w-[18px]" />
          </IconButton>
          <IconButton label="Refresh device" onClick={onRefresh}>
            <RefreshIcon className="h-[18px] w-[18px]" />
          </IconButton>
        </div>
      </div>
      {/* Inset output surface: darker canvas, rounded, no border */}
      <div className="min-h-0 flex-1 px-3 pb-3">
        <div
          ref={scroller}
          className="thin-scroll bg-canvas h-full overflow-y-auto rounded-xl py-3"
        >
          {logs.length === 0 ? (
            <div className="text-ink-faint px-4 font-mono text-[13px]">
              Waiting for logs…
            </div>
          ) : (
            logs.map((entry, index) => <LogLine key={index} entry={entry} />)
          )}
        </div>
      </div>
    </section>
  );
}
