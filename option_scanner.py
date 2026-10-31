"""Compatibility entry point for the Angel Digit Scanner."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("angel_scanner.py")), run_name="__main__")
