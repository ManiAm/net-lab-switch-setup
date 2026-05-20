#!/usr/bin/env python3
"""Entry point: python3 decode_i2c.py Ethernet16"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from decode_i2c.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
