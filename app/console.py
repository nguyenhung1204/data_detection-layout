from __future__ import annotations

import sys


def configure_console() -> None:
    """Keep Vietnamese CLI messages printable in Windows PowerShell consoles."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
