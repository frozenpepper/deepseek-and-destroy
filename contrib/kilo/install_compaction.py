#!/usr/bin/env python3
"""Compatibility wrapper: Kilo adapter is now a first-class harness adapter."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

script = Path(__file__).resolve().parents[2] / "scripts" / "install_harness_adapter.py"
argv = [sys.executable, str(script), "--harness", "kilo", *sys.argv[1:]]
raise SystemExit(subprocess.run(argv, env=os.environ.copy()).returncode)
