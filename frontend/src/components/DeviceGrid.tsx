import { motion } from "motion/react";
import type { DeviceInfo } from "../types";
import { cn } from "../lib/utils";

const APPLE_EASE = [0.32, 0.72, 0, 1] as const;

/** One device-info tile in the grid. */
function InfoCell({
  label,
  value,
  index,
}: {
  label: string;
  value: string;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: APPLE_EASE, delay: index * 0.04 }}
      className={cn(
        "bg-panel-2 rounded-xl px-3.5 py-3",
        "transition-colors duration-200",
      )}
    >
      <div className="text-ink-dim text-[13px] leading-tight">{label}</div>
      <div
        title={value}
        className={cn(
          "mt-1.5 truncate text-[13.5px] font-medium leading-snug",
          value === "—" ? "text-ink-faint" : "text-ink",
        )}
      >
        {String(value ?? "—")}
      </div>
    </motion.div>
  );
}

const FIELDS: Array<keyof DeviceInfo> = [
  "product_type",
  "serial",
  "udid",
  "imei",
  "product_version",
  "build_version",
  "activation_state",
  "name",
];

const LABELS: Record<string, string> = {
  product_type: "Model",
  serial: "Serial",
  udid: "UDID",
  imei: "IMEI",
  product_version: "iOS",
  build_version: "Build",
  activation_state: "Activation",
  name: "Device Name",
};

/** 2-column grid of device identity tiles inside a wrapped container. */
export function DeviceGrid({ device }: { device: DeviceInfo | null }) {
  return (
    <div className="bg-panel rounded-2xl p-2">
      <div className="grid grid-cols-2 gap-2.5">
      {FIELDS.map((field, index) => {
        const raw = device
          ? ((device[field as keyof DeviceInfo] as string | null) ?? "—")
          : "";
        const value = raw === "" ? "—" : raw;
        return (
          <InfoCell
            key={field}
            label={LABELS[field]}
            value={device ? value : "—"}
            index={index}
          />
        );
      })}
      </div>
    </div>
  );
}
