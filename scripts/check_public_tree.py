"""Fail closed when a Git commit would expose private release inputs."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ALLOWED_EMPTY_ASSETS = {
    "jamfbreak/backups/.gitkeep",
    "jamfbreak/bin/.gitkeep",
}
FORBIDDEN_PREFIXES = (
    ".venv/",
    "build/",
    "dist/",
    "jamfbreak/backups/",
    "jamfbreak/bin/",
)
FORBIDDEN_SUFFIXES = (
    ".dll",
    ".exe",
    ".key",
    ".mbdb",
    ".p12",
    ".pem",
    ".pfx",
    ".plist",
)
TEXT_LIMIT = 2 * 1024 * 1024

PRIVATE_PATTERNS = (
    ("Windows user profile path", re.compile(r"C:" + r"\\Users\\")),
    (
        "private-key block",
        re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----"),
    ),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[A-Z0-9]{16}\b")),
    (
        "email address",
        re.compile(
            r"\b(?![A-Za-z0-9._%+-]+@users\.noreply\.github\.com\b)"
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        ),
    ),
    ("40-character device identifier", re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{40}(?![0-9A-Fa-f])")),
)


def publication_candidate_paths(root: Path) -> list[str]:
    """Return tracked files plus untracked, non-ignored first-commit candidates."""

    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return sorted(
        {item for item in result.stdout.decode("utf-8").split("\0") if item}
    )


def check_paths(root: Path, paths: list[str]) -> list[str]:
    problems: list[str] = []
    for relative in paths:
        normalized = relative.replace("\\", "/")
        lowered = normalized.casefold()
        if normalized not in ALLOWED_EMPTY_ASSETS and any(
            lowered.startswith(prefix.casefold()) for prefix in FORBIDDEN_PREFIXES
        ):
            problems.append(f"forbidden private/generated path: {normalized}")
            continue
        if normalized not in ALLOWED_EMPTY_ASSETS and lowered.endswith(FORBIDDEN_SUFFIXES):
            problems.append(f"forbidden binary/private file type: {normalized}")
            continue

        path = root / relative
        try:
            raw = path.read_bytes()
        except OSError as exc:
            problems.append(f"unreadable tracked file {normalized}: {exc}")
            continue
        if len(raw) > TEXT_LIMIT or b"\x00" in raw:
            continue
        text = raw.decode("utf-8", "replace")
        for label, pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                problems.append(f"{label} in {normalized}")
    return problems


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    problems = check_paths(root, publication_candidate_paths(root))
    if problems:
        print("Public-tree privacy check failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1
    print("Public-tree privacy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
