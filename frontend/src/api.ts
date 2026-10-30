import type { AboutInfo, AppState } from "./types";

/**
 * Wrapper around the pywebview JS bridge (`window.pywebview.api`).
 * Falls back to a no-op mock when the GUI is opened outside pywebview
 * (e.g. a plain browser preview) so the UI still renders.
 */

interface PywebviewApi {
  get_state: () => Promise<AppState>;
  refresh: () => Promise<{ ok: boolean }>;
  start_bypass: () => Promise<{ ok: boolean; error?: string }>;
  get_about: () => Promise<AboutInfo>;
  open_github: () => Promise<{ ok: boolean }>;
}

function bridge(): PywebviewApi | null {
  const w = window as unknown as {
    pywebview?: { api?: Partial<PywebviewApi> };
  };
  return (w.pywebview?.api as PywebviewApi | undefined) ?? null;
}

export function isBridgeReady(): boolean {
  return bridge() !== null;
}

const FALLBACK_STATE: AppState = {
  status: "searching",
  status_text: "Searching…",
  device: null,
  logs: [],
};

const DEFAULT_ABOUT: AboutInfo = {
  app_version: "—",
  python_version: "—",
  platform: "browser preview (no pywebview bridge)",
  webview_version: "—",
  frozen: false,
  bin_present: false,
  donors: { legacy: false, "ios26-ipad": false, "ios26-iphone": false },
};

export async function getState(): Promise<AppState> {
  const api = bridge();
  if (!api?.get_state) return FALLBACK_STATE;
  try {
    return await api.get_state();
  } catch {
    return FALLBACK_STATE;
  }
}

export async function refresh(): Promise<{ ok: boolean }> {
  const api = bridge();
  if (!api?.refresh) return { ok: false };
  return api.refresh();
}

export async function startBypass(): Promise<{
  ok: boolean;
  error?: string;
}> {
  const api = bridge();
  if (!api?.start_bypass) return { ok: false, error: "no bridge" };
  return api.start_bypass();
}

export async function getAbout(): Promise<AboutInfo> {
  const api = bridge();
  if (!api?.get_about) return DEFAULT_ABOUT;
  try {
    return await api.get_about();
  } catch {
    return DEFAULT_ABOUT;
  }
}

export async function openGithub(): Promise<{ ok: boolean }> {
  const api = bridge();
  if (!api?.open_github) return { ok: false };
  return api.open_github();
}
