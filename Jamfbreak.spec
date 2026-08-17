from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH)
webview_datas, webview_binaries, webview_hiddenimports = collect_all("webview")

# Never embed the mutable, Git-ignored bin/ or backups/ directories. Frozen
# builds load user-supplied assets from folders beside Jamfbreak.exe.
datas = webview_datas

a = Analysis(
    [str(project_root / "jamfbreak_app.py")],
    pathex=[str(project_root)],
    binaries=webview_binaries,
    datas=datas,
    hiddenimports=webview_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Jamfbreak",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(project_root / "packaging" / "Jamfbreak.version"),
)
