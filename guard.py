#!/usr/bin/env python3
"""Run HA Upgrade Guard directly from source; no pip installation needed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from ha_upgrade_guard.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
