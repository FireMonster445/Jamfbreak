"""
Thin Windows wrapper around the upstream `libimobiledevice` Windows CLI tools
(`idevice_id`, `ideviceinfo`, `idevicebackup2`) which talk to an iOS device
through `usbmuxd` (Apple Mobile Device Support).

The original macOS app used embedded libimobiledevice through IOKit / Swift
bridging. On Windows we instead shell out to the upstream libimobiledevice
command-line utilities so we do NOT depend on linking against libimobiledevice
headers; the user supplies the binaries in `bin/` (see setup.ps1 to fetch them).

Device writes are deliberately confined to one helper at the bottom of this
module.  It always uses the conservative settings-only restore flags and
never invokes firmware/boot-chain tools.  A backup restore is still a real
device mutation, so callers must validate the backup before using it.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .runtime_paths import asset_dir, is_link_or_reparse


class DeviceError(RuntimeError):
    pass


SAFE_RESTORE_FLAGS = (
    "--system",
    "--settings",
    "--skip-apps",
    "--no-reboot",
)


def subprocess_creation_flags() -> int:
    """Hide console windows opened by background helper executables."""
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


@dataclass
class DeviceInfo:
    udid: str               # UniqueDeviceID (the 40-char device UDID)
    serial: str             # SerialNumber
    imei: str               # InternationalMobileEquipmentIdentity ("" if none)
    build_version: str      # BuildVersion (e.g. "22B5075a")
    product_version: str    # ProductVersion (e.g. "18.2")
    product_type: str       # ProductType (e.g. "iPhone12,8")
    activation_state: str   # ActivationState
    name: str               # DeviceName


def _bin(name: str) -> str:
    """Resolve a helper only from Jamfbreak's explicit external bin folder."""
    if not name or Path(name).name != name:
        raise DeviceError("helper name must not contain a path")
    candidate = asset_dir("bin") / name
    variants = [candidate]
    if os.name == "nt" and candidate.suffix.lower() != ".exe":
        variants.append(candidate.with_suffix(".exe"))
    for variant in variants:
        if variant.is_file() and not is_link_or_reparse(variant):
            return str(variant.resolve())
    raise DeviceError(
        f"could not locate a regular '{name}' file in {asset_dir('bin')}. "
        "Install reviewed libimobiledevice Windows binaries there (see setup.ps1)."
    )


def _run(bin_path: str, args: list[str], *, expect_zero: bool = True,
         timeout: float = 30.0) -> str:
    try:
        proc = subprocess.run(
            [bin_path, *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=subprocess_creation_flags(),
        )
    except FileNotFoundError as exc:
        raise DeviceError(f"binary missing: {bin_path}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DeviceError(f"command timed out: {bin_path} {' '.join(args)}") from exc

    if expect_zero and proc.returncode != 0:
        raise DeviceError(
            f"`{os.path.basename(bin_path)} {' '.join(args)}` failed (exit {proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace').strip()}"
        )
    return proc.stdout.decode("utf-8", "replace").strip()


def list_udids() -> list[str]:
    """Return UDIDs of USB-attached iOS devices.

    Tries `idevice_id -l` first. If idevice_id is not available, falls back
    to querying `ideviceinfo -k UniqueDeviceID` (which talks to the first
    connected device, matching the original RodoExploit .bat behavior).
    """
    try:
        out = _run(_bin("idevice_id"), ["-l"], expect_zero=True)
        udids = [line.strip() for line in out.splitlines() if line.strip()]
        if udids:
            return udids
    except DeviceError:
        pass  # idevice_id not available — fall through to ideviceinfo

    # Fallback: use ideviceinfo without -u (defaults to first device)
    try:
        udid = _run(_bin("ideviceinfo"), ["-k", "UniqueDeviceID"], expect_zero=True)
        if udid:
            return [udid.strip()]
    except DeviceError:
        pass
    return []


def _info_field(udid: str, key: str) -> str:
    # If udid is None, ideviceinfo talks to the first connected device.
    args = ["-k", key] if udid is None else ["-u", udid, "-k", key]
    out = _run(_bin("ideviceinfo"), args, expect_zero=True)
    return out.strip()


def get_device_info(udid: str | None = None) -> DeviceInfo:
    """
    Read all fields the bypass needs from the connected device.

    If udid is None, tries idevice_id -l to list devices. If idevice_id
    isn't available, falls back to ideviceinfo without -u (queries the
    first connected device — same as the original RodoExploit .bat).
    """
    if udid is None:
        udids = list_udids()
        if len(udids) == 0:
            raise DeviceError(
                "no iOS device detected. Make sure iTunes (or Apple Mobile "
                "Device Support) is installed, the device is unlocked, and "
                "connected via USB."
            )
        if len(udids) > 1:
            raise DeviceError(
                f"multiple iOS devices detected ({len(udids)}). Pass --udid to "
                f"select one. UDIDs: {', '.join(udids)}"
            )
        udid = udids[0]

    try:
        serial = _info_field(udid, "SerialNumber")
        build_version = _info_field(udid, "BuildVersion")
        product_version = _info_field(udid, "ProductVersion")
        product_type = _info_field(udid, "ProductType")
        activation_state = _info_field(udid, "ActivationState")
        name = _info_field(udid, "DeviceName")
        imei = _info_field(udid, "InternationalMobileEquipmentIdentity")
    except DeviceError as exc:
        raise DeviceError(
            f"could not read device info. Reconnect the device, make sure it "
            f"is unlocked and visible in iTunes. ({exc})"
        ) from exc

    if not udid or not serial or not build_version or not product_type:
        raise DeviceError(
            f"incomplete device info (udid={udid}, sn={serial}, "
            f"build={build_version}, type={product_type}). Re-run a fresh restore "
            f"from ipsw.me and re-connect before patching."
        )

    return DeviceInfo(
        udid=udid,
        serial=serial,
        imei=(imei or ""),
        build_version=build_version,
        product_version=product_version,
        product_type=product_type,
        activation_state=activation_state,
        name=name,
    )


def validate_restore_tool(exe: str) -> None:
    """Fail closed if the supplied idevicebackup2 lacks required options."""
    try:
        proc = subprocess.run(
            [exe, "--help"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            creationflags=subprocess_creation_flags(),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise DeviceError(f"could not inspect idevicebackup2: {exc}") from exc

    help_text = proc.stdout.decode("utf-8", "replace")
    required = (*SAFE_RESTORE_FLAGS, "--source", "--udid")
    missing = [flag for flag in required if flag not in help_text]
    if missing:
        raise DeviceError(
            "idevicebackup2 does not advertise the required safety options "
            f"({', '.join(missing)}). Refusing to run an incompatible binary."
        )


def build_restore_command(
    exe: str,
    backup_root: str,
    udid: str,
    *,
    source_udid: str,
) -> list[str]:
    """Build the only restore command this application is allowed to run."""
    if not udid or not source_udid:
        raise DeviceError("target and source UDIDs must both be non-empty")
    return [
        exe,
        "--udid",
        udid,
        "--source",
        source_udid,
        "restore",
        *SAFE_RESTORE_FLAGS,
        backup_root,
    ]


def restore_backup(
    backup_root: str,
    udid: str,
    *,
    source_udid: str,
    verbose: bool = True,
) -> int:
    """
    Restore a validated backup via the settings-only command.

    ``backup_root`` is the parent directory containing ``source_udid``.  This
    matches idevicebackup2's documented directory layout.  There is no
    timeout: forcibly killing an in-progress restore is less safe than letting
    the mobilebackup2 protocol finish or fail normally.

    Returns the exit code of idevicebackup2 (0 = success, matching the
    original `== 0` success check).
    """
    source_dir = Path(backup_root) / source_udid
    for required_name in ("Info.plist", "Manifest.plist", "Status.plist"):
        if not (source_dir / required_name).is_file():
            raise DeviceError(
                f"validated backup changed before restore: missing "
                f"{source_dir / required_name}"
            )

    exe = _bin("idevicebackup2")
    validate_restore_tool(exe)
    command = build_restore_command(
        exe, backup_root, udid, source_udid=source_udid
    )
    if verbose:
        print(f"[restore] invoking {' '.join(command)}")
    proc = subprocess.run(
        command,
        check=False,
        creationflags=subprocess_creation_flags(),
    )
    return proc.returncode
