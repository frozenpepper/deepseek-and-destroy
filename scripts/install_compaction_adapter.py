#!/usr/bin/env python3
"""Compatibility wrapper for the renamed DSD harness-adapter installer.

New code should use `install_harness_adapter.py`; this entry point remains so old
runs/docs do not fail merely because v13 broadened the adapter beyond compaction.
"""
from install_harness_adapter import main

if __name__ == "__main__":
    raise SystemExit(main())
