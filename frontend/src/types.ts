export interface DeviceInfo {
  udid: string;
  serial: string;
  imei: string | null;
  build_version: string;
  product_version: string;
  product_type: string;
  activation_state: string;
  name: string;
}

export type LogKind = "info" | "success" | "error" | "step";

export interface LogEntry {
  text: string;
  kind: LogKind;
  tag: string | null;
}

export type Status = "searching" | "connected" | "patching" | "success" | "error";

export interface AppState {
  status: Status;
  status_text: string;
  device: DeviceInfo | null;
  logs: LogEntry[];
}

export type ThemeName = "light" | "dark" | "hacker";

export interface AboutInfo {
  app_version: string;
  python_version: string;
  platform: string;
  webview_version: string;
  frozen: boolean;
  bin_present: boolean;
  donors: Record<string, boolean>;
}
