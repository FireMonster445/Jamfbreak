import { useCallback, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import type { AboutInfo, AppState, LogEntry, ThemeName } from "./types";
import * as api from "./api";
import { StatusPill } from "./components/StatusPill";
import { DeviceGrid } from "./components/DeviceGrid";
import { ActionButton } from "./components/ActionButton";
import { Console } from "./components/Console";
import { SettingsDialog } from "./components/SettingsDialog";
import { HackerText } from "./components/HackerText";
import { HackerShell } from "./components/HackerShell";
import { IconButton } from "./components/IconButton";
import { BookIcon, SettingsIcon } from "./components/icons";
import { cn } from "./lib/utils";
import logoUrl from "./assets/logo.png";

const REPO_URL = "https://github.com/FireMonster445/Jamfbreak";
const POLL_MS = 250;
const APPLE_EASE = [0.32, 0.72, 0, 1] as const;

function currentTheme(): ThemeName {
  const saved = window.localStorage.getItem("jamfbreak-theme");
  return saved === "light" || saved === "dark" || saved === "hacker"
    ? saved
    : "dark";
}

export default function App() {
  const [state, setState] = useState<AppState>({
    status: "searching",
    status_text: "Searching…",
    device: null,
    logs: [],
  });
  const [theme, setThemeState] = useState<ThemeName>(currentTheme);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [about, setAbout] = useState<AboutInfo | null>(null);
  const [working, setWorking] = useState(false);
  const mounted = useRef(false);

  // Header version fits the polish; fetched once at startup.
  useEffect(() => {
    api.getAbout().then(setAbout).catch(() => {});
  }, []);

  // Theme lives on <html data-theme>; tokens in index.css follow it.
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const poll = useCallback(async () => {
    const next = await api.getState();
    if (mounted.current) setState(next);
  }, []);

  // Bridge readiness + 250ms state polling, same cadence as the old GUI.
  useEffect(() => {
    mounted.current = true;
    let cancelled = false;
    let timer: number | undefined;

    const waitAndStart = async () => {
      for (let i = 0; i < 40; i++) {
        if (api.isBridgeReady()) break;
        await new Promise((r) => setTimeout(r, 250));
        if (cancelled) return;
      }
      await poll();
      const loop = async () => {
        if (cancelled) return;
        await poll();
        timer = window.setTimeout(loop, POLL_MS);
      };
      loop();
    };
    waitAndStart();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
      mounted.current = false;
    };
  }, [poll]);

  function setTheme(next: ThemeName) {
    setThemeState(next);
    window.localStorage.setItem("jamfbreak-theme", next);
  }

  async function onOpenSettings() {
    setSettingsOpen(true);
    // Fetch/dedupe About info lazily each time the dialog opens.
    setAbout(await api.getAbout());
  }

  async function onOpenGithub() {
    await api.openGithub();
    // Fallback when no bridge: open normally from the webview context.
    window.open(REPO_URL, "_blank");
  }

  async function onBypass() {
    setWorking(true);
    const result = await api.startBypass();
    if (!result.ok) {
      setWorking(false);
    }
  }

  async function onRefresh() {
    await api.refresh();
  }

  const isPatching =
    working ||
    state.status === "patching";
  const noDevice = state.device === null;
  const hacker = theme === "hacker";

  // Hacker theme renders the whole app like a single CLI tool.
  if (hacker) {
    return (
      <div className="bg-canvas text-ink h-full w-full overflow-hidden">
        <HackerShell
          state={state}
          about={about}
          onBypass={onBypass}
          onRefresh={onRefresh}
          onOpenSettings={onOpenSettings}
          onOpenGithub={onOpenGithub}
        />
        <SettingsDialog
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          theme={theme}
          onThemeChange={setTheme}
          about={about}
        />
      </div>
    );
  }

  return (
    <div className="bg-canvas text-ink flex h-full w-full gap-4 overflow-hidden px-6 py-5">
      {/* Left column — brand, device info, actions */}
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: APPLE_EASE }}
        className="flex w-[440px] shrink-0 flex-col"
      >
        {/* Brand row — real logo art, no outline/border plate */}
        <div className="flex items-center gap-3.5">
          <img
            src={logoUrl}
            alt="Jamfbreak logo"
            className="h-11 w-11 shrink-0 rounded-xl"
            draggable={false}
          />
          <div className="flex items-baseline gap-2">
            <span className="text-ink text-[26px] font-bold tracking-tight">
              JamfBreak
            </span>
            <span className="text-ink-faint font-mono text-[12px]">
              v{about?.app_version ?? "1.0.7"}
            </span>
          </div>
          <div className="ml-2">
            <StatusPill status={state.status} />
          </div>
        </div>

        {/* Subtitle */}
        <p
          className={cn(
            "text-ink-dim mt-2 text-[14px]",
            hacker && "text-ink-dim",
          )}
        >
          {hacker ? (
            <HackerText text="// removing mdm profiles is a single command away" />
          ) : (
            "// Remove MDM's and restriction profiles with a single click"
          )}
        </p>

        {/* Device info grid */}
        <div className="mt-5">
          <DeviceGrid device={state.device} />
        </div>

        {/* Action buttons */}
        <div className="mt-5 flex items-center justify-center gap-3">
          <ActionButton
            variant="primary"
            onClick={onBypass}
            disabled={isPatching || noDevice}
          >
            {hacker ? (
              <HackerText text={isPatching ? "running..." : "bypass"} speedMs={18} />
            ) : (
              "Bypass"
            )}
          </ActionButton>
          <ActionButton
            variant="secondary"
            onClick={onRefresh}
            disabled={isPatching}
          >
            {hacker ? <HackerText text="re-scan" speedMs={18} /> : "Refresh"}
          </ActionButton>
        </div>

        {/* Spacer pushes footer icons to the bottom */}
        <div className="flex-1" />

        {/* Footer icons */}
        <div className="flex items-center gap-2 pb-1">
          <IconButton label="Open settings" onClick={onOpenSettings}>
            <SettingsIcon className="h-[19px] w-[19px]" />
          </IconButton>
          <IconButton label="Open GitHub repository" onClick={onOpenGithub}>
            <BookIcon className="h-[19px] w-[19px]" />
          </IconButton>
        </div>
      </motion.div>

      {/* Right column — console */}
      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: APPLE_EASE, delay: 0.08 }}
        className="min-w-0 flex-1"
      >
        <Console logs={state.logs} onRefresh={onRefresh} />
      </motion.div>

      <SettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        theme={theme}
        onThemeChange={setTheme}
        about={about}
      />
    </div>
  );
}

export type { LogEntry };
