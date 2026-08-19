<p align="center">
  <img src="Jamfbreak%20Logo.png" alt="Jamfbreak logo" width="180">
</p>

# Jamfbreak — Windows MDM settings-restore tool

A **Windows CLI + GUI tool** that bypasses MDM (Mobile Device Management)
profiles on supervised iOS devices without intentionally erasing the device.
It performs a real backup restore, so zero data loss or zero boot failure can
never be guaranteed.

Based on the [VitreosExploit](https://github.com/FireMonster445/RodoExploit)
method: edit a pre-made clean backup's `Manifest.plist` with the device's
real Serial + UDID, then restore it with `idevicebackup2 restore --system
--settings --skip-apps --no-reboot`. These flags are intended to avoid an
intentional erase, but backup restore can still change or lose data.

> **Legal notice.** Use ONLY on devices you own and are authorized to modify.
> Use on managed/corporate/institutional devices without permission is
> prohibited and may be illegal.

---

## Bootloop and data-loss risk controls

The tool never writes firmware or the boot chain. It further reduces restore
risk with fail-closed checks:

1. **No firmware writes** — never calls `idevicerestore`, `irecovery`, or IPSW.
2. **Settings-only restore** — `--system --settings --skip-apps` overwrites
   configuration plists, not the OS image.
3. **Pre-restore validation** — Manifest/Info/Status plists, completed snapshot
   state, encryption state, and the backup payload index are checked before
   the restore command.
4. **Post-edit verification** — the edited Manifest.plist is re-read and
   confirmed before restore.
5. **Private working copy** — the donor backup is never edited in place, and
   Manifest.plist is replaced atomically after a complete write.
6. **Identity recheck** — target UDID, serial, and model are re-read immediately
   before restore.
7. **Controlled reboot** — only requests a restart after a successful restore
   exit. A failed restore is treated as potentially partial and is never
   automatically rebooted.

These controls materially lower risk; they are not a warranty. Before using a
real device, make a separate current backup and ensure you have authorization
to remove its management profile.

---

## Requirements

- Windows 10/11, 64-bit
- Python 3.10+ (Python 3.12 tested)
- Pinned Python dependencies from `requirements.txt`
- **iTunes** installed (or `Apple Mobile Device Support` standalone) so the
  Apple USB driver is available for `usbmuxd`
- **libimobiledevice-win** binaries in `jamfbreak/bin/`:
  `idevice_id.exe`, `ideviceinfo.exe`, `idevicebackup2.exe`,
  `idevicerestart.exe` (and their DLL dependencies)
- A **reviewed donor backup folder** placed under `jamfbreak/backups/`.
  Get one from [VitreosExploit](https://github.com/FireMonster445/RodoExploit)
  — copy the reviewed donor folder into `backups/`.

---

## Setup

```powershell
cd "C:\path\to\JamfBreakv2"
python -m pip install -r requirements.txt
.\jamfbreak\setup.ps1
```

`setup.ps1` does not silently download or install executable code. It checks
the locally supplied helper binaries, prints their SHA-256 hashes, checks for
a donor backup, and reports missing Python dependencies. Compare native helper
hashes with the upstream publisher before running them.

---

## Usage

### GUI (recommended)

```powershell
python -m jamfbreak.gui
```

Minimalist black & white window with device connection status, device
info panel, live console (fade-in animations), and a Bypass button. No
license key, account, or network connection is required.

### CLI

```powershell
# Default — validated settings restore
python -m jamfbreak.patcher

# Specify a backup folder explicitly
python -m jamfbreak.patcher --backup-dir "C:\path\to\donor-backup"

# Skip the automatic reboot
python -m jamfbreak.patcher --no-reboot

# Retain the patched working copy for diagnostics (original is always preserved)
python -m jamfbreak.patcher --keep-backup-copy

# Select a specific device if multiple are connected
python -m jamfbreak.patcher --udid 00008101-00012345ABCDEF
```

---

## How it works

```
device.py         ── wraps idevice_id / ideviceinfo / idevicebackup2 / idevicerestart
rodo_pipeline.py  ── the bypass pipeline: detect → validate → edit → verify → restore → reboot
patcher.py        ── CLI entrypoint (thin wrapper around rodo_pipeline)
gui.py            ── pywebview GUI launcher
gui_html.py       ── embedded HTML/CSS/JS (black & white minimalist design)
```

Pipeline steps:
1. **Detect** — read device Serial + UDID via `ideviceinfo`
2. **Validate** — verify the backup folder has a parseable Manifest.plist
   with the required keys (SerialNumber, UniqueDeviceID)
3. **Edit** — inject the device's real Serial + UDID into Manifest.plist
   using Python's `plistlib`
4. **Verify** — re-read the edited Manifest.plist and confirm the values
   are correct (bootloop guard)
5. **Restore** — `idevicebackup2 --udid TARGET --source SOURCE restore
   --system --settings --skip-apps --no-reboot BACKUP_PARENT`
6. **Reboot** — `idevicerestart` only after a successful restore

---

## Testing

```powershell
python -m tests.smoke_test
```

Offline self-tests cover:
- Manifest.plist editing (injection, nested key preservation, missing key errors)
- Backup folder validation (missing manifest, corrupt plist, missing keys)
- Post-edit verification (correct values, wrong values)
- Backup folder discovery
- completed-backup, encryption, and payload-index validation
- exact safe restore command construction (no `--full` or `--remove`)
- device identity drift and failed-restore no-reboot behavior

## Build the Windows executable

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean Jamfbreak.spec
```

The single-file GUI is written to `dist/Jamfbreak.exe`. For privacy and supply-
chain safety, the build never embeds the Git-ignored `bin/` or `backups/`
directories. Create `bin/` and `backups/` beside the frozen EXE and place only
reviewed runtime assets there. UPX compression is disabled to reduce opaque
packing and antivirus false positives.

Do not publish an unsigned EXE. Follow [SIGNING.md](SIGNING.md), verify the
signature, and submit genuine false positives to the antivirus vendor. Signing
improves publisher identity and reputation but cannot guarantee that every
security product will allow the application.

---

## Project layout

```
JamfBreakv2/
├── jamfbreak/
│   ├── __init__.py
│   ├── patcher.py        ── CLI entrypoint
│   ├── gui.py            ── pywebview GUI launcher
│   ├── gui_html.py       ── embedded HTML/CSS/JS
│   ├── device.py         ── wraps libimobiledevice-win CLI binaries
│   ├── rodo_pipeline.py  ── bypass pipeline + bootloop safety checks
│   ├── setup.ps1         ── Windows install/setup helper
│   ├── bin/              ── source-run helper location; contents are Git-ignored
│   └── backups/          ── source-run donor location; contents are Git-ignored
└── tests/
    ├── __init__.py
    └── smoke_test.py     ── offline safety and regression tests
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `could not locate 'idevice_id'` | Run `setup.ps1`, drop binaries into `bin/` |
| `No clean backup folder found` | Copy the reviewed donor folder into `backups/` |
| `no iOS device detected` | Install iTunes, unlock device, reconnect USB |
| `Manifest.plist does not contain SerialNumber` | Backup folder is corrupt or incompatible — re-download from RodoExploit |
| `idevicebackup2 returned non-zero` | Do not repeatedly retry or force a reboot. The restore may be partial. Keep the device connected/unlocked and inspect the full output first. |
