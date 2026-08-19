<p align="center">
  <img src="Jamfbreak%20Logo.png" alt="Jamfbreak logo" width="180">
</p>

# Jamfbreak

**Windows iOS MDM Bypass & MDM Removal Tool**

Jamfbreak is a Windows CLI and GUI tool for bypassing Mobile Device Management (MDM) restrictions on supervised iPhone and iPad devices.

It provides a settings-based MDM bypass and restore workflow designed to avoid an intentional device erase. Jamfbreak is built around the VitreosExploit method and uses libimobiledevice to perform a validated backup restore.

> ⚠️ **Important:** Jamfbreak does not guarantee zero data loss, zero boot failure, or successful MDM removal. Always create a current backup before modifying a device.

---

## ✨ Features

- 🪟 **Windows support** — designed for Windows 10 and Windows 11
- 📱 **iPhone & iPad support** — works with compatible supervised iOS/iPadOS devices
- 🔓 **MDM bypass** — bypass MDM restrictions using a settings restore
- 🛠️ **MDM removal workflow** — removes the local management configuration from the restored device state
- 💾 **No intentional factory reset** — Jamfbreak does not use a firmware restore as part of its bypass process
- 🖥️ **GUI & CLI** — use the minimalist graphical interface or command line
- 🔒 **Fail-closed safety checks** — validation is performed before modifying or restoring a backup
- 🌐 **No account or license required** — Jamfbreak does not require an online account or license key
- 🧪 **Offline testing** — core backup and restore logic includes automated safety tests

---

## 🔎 What is Jamfbreak?

Jamfbreak is an open-source Windows MDM bypass / MDM patcher for supervised Apple devices.

It is intended for authorized device owners and security researchers who need to remove or bypass an unwanted local MDM configuration without intentionally restoring the device firmware.

Unlike traditional MDM patchers that may require a complete device restore first, Jamfbreak uses a validated backup-restore workflow based on the VitreosExploit technique.

### Jamfbreak keywords

Jamfbreak is designed around:

- iOS MDM bypass
- iPadOS MDM bypass
- iPhone MDM removal
- iPad MDM removal
- MDM profile removal
- MDM patcher
- Windows MDM bypass
- Windows iOS MDM tool
- supervised iPhone MDM
- supervised iPad MDM
- Mobile Device Management bypass
- Apple MDM research

---

## 🆚 Why Jamfbreak?

Many existing MDM patching tools rely on a full restore workflow.

Jamfbreak takes a different approach.

Instead of intentionally erasing the device and writing firmware, Jamfbreak prepares a working backup, validates it, updates the device identity information and performs a settings-only backup restore.

This is intended to reduce unnecessary data loss and boot-related risks.

However, this is not risk-free. A backup restore can still partially modify or damage device data.

---

## ⚙️ How Jamfbreak works

Jamfbreak uses the following high-level pipeline:

```
Connect iPhone / iPad
        ↓
Detect device identity
        ↓
Validate donor backup
        ↓
Create private working copy
        ↓
Update device identity
        ↓
Verify modified backup
        ↓
Restore settings
        ↓
Verify restore result
        ↓
Controlled restart
```

The project is based on the VitreosExploit approach of modifying a prepared backup's `Manifest.plist` with the target device's identity before performing the restore.

Jamfbreak performs additional validation around this process to reduce accidental restore failures.

---

## 🛡️ Safety & Restore Protection

Jamfbreak deliberately avoids firmware-level restore operations.

### 🚫 No firmware flashing

Jamfbreak does not intentionally write firmware or the boot chain.

It does not call:

- `idevicerestore`
- `irecovery`
- IPSW firmware restoration

### ✅ Restore validation

Before restoring, Jamfbreak validates:

- `Manifest.plist`
- backup metadata
- completed snapshot state
- encryption state
- payload index
- required device identity fields

### 🔐 Identity verification

The target device's:

- **Serial Number**
- **UDID**
- **Model**

are checked before the restore.

### 🧾 Atomic Manifest modification

The original donor backup is never modified directly.

Jamfbreak creates a private working copy and replaces the modified `Manifest.plist` atomically after the complete write has finished.

### ⚠️ Failed restore protection

A failed restore is treated as potentially partial.

Jamfbreak does not automatically reboot the device after an unsuccessful restore.

These mechanisms reduce risk but cannot guarantee that the device will boot normally or that no data will be lost.

---

## 💻 Requirements

### 🖥️ Operating system

- Windows 10 64-bit
- Windows 11 64-bit

### 🧰 Software

- Python 3.10+
- Python 3.12 tested
- Dependencies from `requirements.txt`
- iTunes or Apple Mobile Device Support

### 📡 Apple device communication

Jamfbreak requires the Windows libimobiledevice binaries:

- `idevice_id.exe`
- `ideviceinfo.exe`
- `idevicebackup2.exe`
- `idevicerestart.exe`

and their required DLL dependencies.

---

## 🚀 Installation

Clone the repository and install the Python dependencies:

```bash
cd "C:\path\to\JamfBreakv2"
python -m pip install -r requirements.txt
```

Then run:

```powershell
.\jamfbreak\setup.ps1
```

The setup script does not silently download or execute external binaries.

It checks the locally supplied helper binaries, displays their SHA-256 hashes, checks for the required donor backup and reports missing Python dependencies.

> ⚠️ Always verify third-party binaries against their original publisher before executing them.

---

## 🖥️ GUI

Launch the Jamfbreak graphical interface with:

```bash
python -m jamfbreak.gui
```

### GUI features

- 📶 device connection status
- 📱 device information
- 🧾 live console output
- 🔄 restore status
- 🧭 simple bypass workflow

No Jamfbreak account, license key or network connection is required.

---

## ⌨️ CLI

Jamfbreak can also be used directly from the command line:

```bash
python -m jamfbreak.patcher
```

### 📁 Specify a backup directory

```bash
python -m jamfbreak.patcher --backup-dir "C:\path\to\donor-backup"
```

### ⛔ Skip automatic restart

```bash
python -m jamfbreak.patcher --no-reboot
```

### 🧪 Keep working backup for diagnostics

```bash
python -m jamfbreak.patcher --keep-backup-copy
```

### 📲 Select a specific device

```bash
python -m jamfbreak.patcher --udid YOUR-DEVICE-UDID
```

---

## 🧪 Testing

Run the offline test suite:

```bash
python -m tests.smoke_test
```

### ✅ Test coverage

- Manifest editing
- Manifest validation
- missing and corrupt backups
- required key validation
- post-edit verification
- backup discovery
- completed-backup validation
- encryption-state validation
- payload-index validation
- restore command construction
- device identity changes
- failed-restore handling

---

## 🏗️ Project Structure

```
JamfBreakv2/
├── jamfbreak/
│   ├── __init__.py
│   ├── patcher.py
│   ├── gui.py
│   ├── gui_html.py
│   ├── device.py
│   ├── rodo_pipeline.py
│   ├── setup.ps1
│   ├── bin/
│   └── backups/
│
└── tests/
    ├── __init__.py
    └── smoke_test.py
```

### 🧩 Core components

| File | Purpose |
|------|---------|
| `device.py` | Apple device communication |
| `rodo_pipeline.py` | Validation and restore pipeline |
| `patcher.py` | CLI entry point |
| `gui.py` | Windows GUI launcher |
| `gui_html.py` | GUI interface |
| `setup.ps1` | Local environment validation |
| `smoke_test.py` | Offline regression and safety tests |

---

## 🔧 Troubleshooting

### ❌ `idevice_id` cannot be found

Install Apple Mobile Device Support and run:

```powershell
.\jamfbreak\setup.ps1
```

Make sure the required libimobiledevice-win binaries are present in `jamfbreak/bin/`.

### 📵 No iOS device detected

Make sure:

1. The Apple USB driver is installed
2. The device is unlocked
3. The USB connection is working
4. The computer is trusted by the device

### 📦 No donor backup found

Place the reviewed donor backup in the expected `backups/` directory.

### ⚠️ `Manifest.plist` is invalid

The backup may be incomplete, corrupted or incompatible with Jamfbreak.

### ❌ `idevicebackup2` returns an error

Do not repeatedly retry the restore or force a reboot.

A failed backup restore can be partially applied. Keep the device connected and inspect the complete command output first.

---

## 🏭 Building Jamfbreak for Windows

Install the build dependencies:

```bash
python -m pip install -r requirements-build.txt
```

Build the executable:

```bash
python -m PyInstaller --noconfirm --clean Jamfbreak.spec
```

### 📦 Output

```
dist/Jamfbreak.exe
```

The build does not embed the Git-ignored `bin/` or `backups/` directories.

For security and supply-chain transparency, only reviewed runtime assets should be distributed with the application.

UPX compression is disabled to reduce opaque executable packing and potential antivirus false positives.

---

## 🔏 Code signing

Do not distribute an unsigned production executable.

Follow `SIGNING.md` and verify the resulting signature before publishing releases.

Code signing improves publisher identity and reputation but cannot guarantee that antivirus products will classify the application as safe.

---

## ⚠️ Legal & Security Disclaimer

Jamfbreak is intended only for devices that you own or are explicitly authorized to modify.

Do not use Jamfbreak to bypass MDM restrictions on company-owned, school-owned, organizational or otherwise managed devices without permission from the responsible administrator.

Unauthorized removal or bypass of Mobile Device Management controls may violate organizational policies, contracts or applicable law.

Jamfbreak is provided for legitimate device administration, research and authorized security testing.

**Use at your own risk.**

No guarantee is provided regarding:

- successful MDM bypass
- successful MDM removal
- device compatibility
- data preservation
- bootability
- future iOS/iPadOS versions
- persistence after subsequent restores or management enrollment

Always create a separate, current backup before attempting any restore operation.

---

## 📚 Credits

Jamfbreak's restore approach is based on research and the VitreosExploit method.

Thanks to the developers and contributors of the open-source Apple device communication tools used by this project, including libimobiledevice.

---

## 🤝 Contributing

Issues, bug reports, testing and improvements are welcome.

If you discover a problem with Jamfbreak, please open a GitHub Issue with:

- Windows version
- iOS/iPadOS version
- device model
- Jamfbreak version
- complete error output
- relevant logs

Do not include personal information, UDIDs, serial numbers or private backup data in public issues.

---

## 📌 About

Jamfbreak is a Windows-based iOS/iPadOS MDM bypass and MDM patching research project.

It provides a GUI and CLI workflow for authorized users who need to work with supervised Apple devices and their Mobile Device Management configuration.

**Keywords:** Jamfbreak, MDM, MDM bypass, MDM removal, MDM patcher, iOS MDM, iPad MDM, iPhone MDM, iPadOS MDM, Windows MDM bypass, Mobile Device Management, Apple MDM, supervised iPhone, supervised iPad, MDM profile removal.