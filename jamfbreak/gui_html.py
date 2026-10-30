"""
HTML frontend for the Jamfbreak GUI.

The frontend is a compiled React app (Animate UI components + Motion,
Tailwind CSS) built by `python scripts/build_gui.py` from frontend/ and
bundled here as a compressed Python module. jamfbreak.gui decodes it to
an HTML file in the temp directory and loads it in pywebview via a
file:// URL — never via the html= parameter (NavigateToString navigates
to an opaque about:blank origin where this Vite module bundle refuses
to execute).
"""

from .gui_bundle import HTML

__all__ = ["HTML"]
