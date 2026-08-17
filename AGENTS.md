# AGENTS.md — Jamfbreak

Notes for opencode and other AI agents working in this repository.

## Project

`jamfbreak/` is a Windows CLI + GUI tool that bypasses MDM
(Mobile Device Management) profiles on supervised iOS devices without
a factory reset. It's Python-only on Windows. The user supplies the
pre-made clean backup folder and the libimobiledevice-win binaries.

The method is based on [RodoExploit](https://github.com/FireMonster445/RodoExploit):
edit a clean backup's Manifest.plist with the device's real Serial +
UDID, then restore it with `idevicebackup2 restore --system --settings
--skip-apps --no-reboot`. The flow avoids an intentional erase, but a real
backup restore still has non-zero data-loss and boot risk.

## What must NOT change without great care

- **`jamfbreak/rodo_pipeline.py`**:
  - `edit_manifest_plist()` injects Serial + UDID into Manifest.plist.
    The `_update_nested` recursive search must find keys at any depth.
  - `_validate_backup_folder()` runs BEFORE any device modification. It
    must verify Manifest.plist exists, is parseable, and contains the
    keys we need. A failure here must ABORT — never proceed to restore.
  - `_verify_manifest_edit()` runs AFTER editing but BEFORE restore. It
    re-reads the plist and confirms the injected values are present. A
    failure here must ABORT — never proceed to restore.
  - The restore must use `--no-reboot` so we control the reboot. Only
    reboot AFTER `idevicebackup2` returns exit 0.

## Bootloop safety — risk-reduction controls

1. No firmware writes — never calls idevicerestore/irecovery/IPSW.
2. Settings-only restore — `--system --settings --skip-apps` overwrites
   configuration plists, not the OS image or boot chain.
3. Pre-restore validation — backup folder structure is verified before
   any device communication.
4. Post-edit verification — the edited Manifest.plist is re-read and
   confirmed before restore.
5. iOS-side validation — idevicebackup2 performs its own backup checks, but a
   non-zero restore exit must be treated as potentially partial.
6. Controlled reboot — only restarts after a successful restore (exit 0).

## Commands the agent should run

```powershell
# Type-check / syntax check
python -m compileall -q jamfbreak tests

# Self-test (safety, privacy, and regression coverage)
python -m tests.smoke_test
```

If you add a new module or change the public API, add a self-test to
`tests/smoke_test.py` that exercises the new behavior. Do not lower the
bar on validation — those are explicit anti-bootloop guarantees.

## Setting up for real-device testing (the agent should NOT do this autonomously)

Real-device bypass requires:

1. `pip install pywebview`
2. The user dropping the libimobiledevice-win binaries into
   `jamfbreak/bin/` (`setup.ps1` walks them through it).
3. The user placing a reviewed donor backup folder into
   `jamfbreak/backups/`.
4. An iOS device connected via USB, unlocked, visible in iTunes.

Do NOT plug a real device in and run `python -m jamfbreak.patcher`
without explicit user direction — the restore step modifies the device's
settings partition.

## Safety guarantees that must hold

- The tool does NOT call `idevicerestore`, `irecovery`, IPSW, or anything
  that touches the boot chain. It only reads device info and calls
  `idevicebackup2 restore --system --settings --skip-apps --no-reboot`.
- Repository validation rejects known malformed backups before restore. If the
  restore tool returns non-zero, the device state is treated as uncertain.
- The tool validates the backup folder and verifies the edited plist
  BEFORE calling `idevicebackup2`.
- The tool only reboots the device AFTER a successful restore (exit 0).
- No intentional factory reset is requested; data preservation is not
  guaranteed by any backup-restore operation.
