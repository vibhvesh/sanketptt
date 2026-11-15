#!/usr/bin/env python3
"""Print a hardware inventory snapshot for field diagnostics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running this file directly from the repository checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sanket_broadcast.hardware import collect_hardware_inventory


def main() -> int:
    try:
        print(json.dumps(collect_hardware_inventory(), indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
