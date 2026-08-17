"""Frozen Windows GUI entry point for Jamfbreak."""

from __future__ import annotations

import multiprocessing

from jamfbreak.gui import main


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
