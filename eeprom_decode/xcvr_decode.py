#!/usr/bin/env python3
"""Entry point: python3 xcvr_decode.py Ethernet16"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from xcvr_decode.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
