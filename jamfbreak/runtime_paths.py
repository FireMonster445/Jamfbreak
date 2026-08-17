"""Resolve user-supplied runtime assets without bundling them into releases."""

from __future__ import annotations

import stat
import sys
from pathlib import Path


def asset_dir(name: str) -> Path:
    """Return an asset directory beside the EXE, or inside the source package."""
    if not name or Path(name).name != name:
        raise ValueError("asset directory name must be a single path component")
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / name
    return Path(__file__).resolve().parent / name


def is_link_or_reparse(path: Path) -> bool:
    """Reject symlinks and Windows reparse points at trust boundaries."""
    try:
        metadata = path.lstat()
    except OSError:
        return True
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag)
