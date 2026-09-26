"""Compatibility entry point — delegates to scanner_main (canonical scanner source)."""
from __future__ import annotations

from scanner_main import DiagnosticApp, embedded_logo_data

__all__ = ["DiagnosticApp", "embedded_logo_data"]

if __name__ == "__main__":
    DiagnosticApp().run()
