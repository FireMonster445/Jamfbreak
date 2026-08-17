<#
.SYNOPSIS
  Verifies the local Jamfbreak runtime prerequisites.

.DESCRIPTION
  Jamfbreak does not silently download or install native executables. Obtain
  libimobiledevice for Windows from a source you trust, verify its published
  hashes or signatures, and place the required EXEs and DLLs in jamfbreak/bin.
#>

param(
    [string] $BinDir = (Join-Path $PSScriptRoot "bin"),
    [switch] $NonInteractive
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host "[setup] $Message" -ForegroundColor Cyan
}

$requiredBins = @(
    "idevice_id.exe",
    "ideviceinfo.exe",
    "idevicebackup2.exe",
    "idevicerestart.exe"
)

if (-not (Test-Path -LiteralPath $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir | Out-Null
}

Write-Step "Checking reviewed libimobiledevice helpers in $BinDir"
$missing = @()
foreach ($bin in $requiredBins) {
    $full = Join-Path $BinDir $bin
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
        $missing += $bin
        continue
    }
    $item = Get-Item -LiteralPath $full
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$bin must not be a link or reparse point"
    }
    $hash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash
    Write-Host "  $bin  SHA256=$hash"
}

if ($missing.Count -gt 0) {
    Write-Warning "Missing required helpers: $($missing -join ', ')"
    Write-Host "Download a reviewed Windows build from the upstream project:"
    Write-Host "  https://github.com/libimobiledevice-win/imobiledevice/releases"
    Write-Host "  https://github.com/libimobiledevice-win/usbmuxd/releases"
    Write-Host "Verify the publisher-provided hashes, then copy the EXEs and DLLs to:"
    Write-Host "  $BinDir"
    if (-not $NonInteractive) {
        Read-Host "Press Enter after adding and verifying the files"
    }
}

$BackupsDir = Join-Path $PSScriptRoot "backups"
if (-not (Test-Path -LiteralPath $BackupsDir)) {
    New-Item -ItemType Directory -Path $BackupsDir | Out-Null
}
Write-Step "Checking for a user-supplied donor backup"
$backupDirs = Get-ChildItem -LiteralPath $BackupsDir -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "Manifest.plist") }
if (-not $backupDirs) {
    Write-Warning "No donor backup with Manifest.plist was found in $BackupsDir"
    Write-Warning "Only use a donor backup whose source and contents you trust."
} else {
    Write-Step "Found donor backup: $($backupDirs[0].Name)"
}

Write-Step "Checking the pinned Python runtime dependency"
$requirements = Join-Path (Split-Path $PSScriptRoot -Parent) "requirements.txt"
& python -c "import webview; print(webview.__version__)"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "pywebview is not installed. Review $requirements, then run:"
    Write-Host "  python -m pip install -r `"$requirements`""
}

Write-Host ""
Write-Host "Verification complete. Review every warning before running Jamfbreak." -ForegroundColor Green
