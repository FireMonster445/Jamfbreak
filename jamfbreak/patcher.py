"""
jamfbreak.patcher — main CLI.

Thin wrapper around the RodoExploit MDM settings-restore pipeline.
The flow avoids an intentional erase but still performs a real device restore.

The bypass works by:
  1. Reading device SerialNumber + UniqueDeviceID via ideviceinfo
  2. Injecting them into a pre-made clean backup's Manifest.plist
  3. Restoring that backup with idevicebackup2 --system --settings
     --skip-apps --no-reboot (limits the restore and prevents auto-reboot)
  4. Restarting the device

Bootloop safety: see the docstring in rodo_pipeline.py.
"""

from __future__ import annotations

import argparse
import sys

from . import rodo_pipeline


def _safe_print(msg: str) -> None:
    sys.stdout.buffer.write((msg + "\n").encode("utf-8", "replace"))
    sys.stdout.flush()


def _cli_log(text: str, kind: str, tag: str | None) -> None:
    prefix = f"[{tag}] " if tag else ""
    _safe_print(f"{prefix}{text}")


def _cmdline(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jamfbreak",
        description="Windows MDM settings-restore tool with strict backup "
                    "validation and controlled reboot safeguards.",
    )
    parser.add_argument("--udid", default=None,
                        help="select a specific device by UDID if multiple are attached")
    parser.add_argument("--backup-dir", default=None,
                        help="path to the pre-made clean backup folder. "
                             "Auto-discovers under jamfbreak/backups/ if not specified.")
    parser.add_argument("--keep-backup-copy", action="store_true",
                        help="retain the patched working copy for diagnostics; "
                             "the original backup is always preserved")
    parser.add_argument("--no-reboot", action="store_true",
                        help="skip the idevicerestart step after restore")
    args = parser.parse_args(argv)

    result = rodo_pipeline.run_rodo_pipeline(
        _cli_log,
        udid_filter=args.udid,
        backup_dir=args.backup_dir,
        keep_backup_copy=args.keep_backup_copy,
        no_reboot=args.no_reboot,
    )
    return result.exit_code


def main():
    sys.exit(_cmdline())


if __name__ == "__main__":
    main()
