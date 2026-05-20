"""CLI entry for decode_i2c."""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, Optional

from . import __version__
from . import sff8472, sff8636
from .backends import open_reader
from .bytemap_format import format_bytemap_sff8636
from .format_output import format_json, format_text
from .i2c_reader import EepromReadError

# SFF-8636 QSFP family identifiers (byte 0, lower page)
QSFP_IDENTIFIERS = frozenset({0x0C, 0x0D, 0x11, 0x18})
SFP_IDENTIFIERS = frozenset({0x03})


def _is_qsfp(identifier: int) -> bool:
    return identifier in QSFP_IDENTIFIERS


def _is_sfp(identifier: int) -> bool:
    return identifier in SFP_IDENTIFIERS


def _decode(raw: Dict[str, Any]) -> Dict[str, Any]:
    ident = raw["lower"][0]
    if _is_qsfp(ident):
        return sff8636.decode_all(raw)
    if _is_sfp(ident):
        return sff8472.decode_a0(raw["lower"])
    return {
        "standard": "unknown",
        "identifier_raw": ident,
        "lower_page_hex": raw["lower"].hex(),
        "upper_pages_hex": {p: raw["upper"][p].hex() for p in raw["upper"]},
        "note": "No decoder for this identifier; use --raw for full hex",
    }


def _build_page_list(no_page1: bool, no_page2: bool) -> List[int]:
    pages = [0, 3]
    if not no_page1:
        pages.insert(1, 1)
    if not no_page2:
        pages.insert(2 if 1 in pages else 1, 2)
    return pages


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read and decode transceiver EEPROM via I2C (SFF-8636 / SFF-8472)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s Ethernet16
  %(prog)s --eeprom-path /sys/bus/i2c/devices/i2c-30/30-0050/eeprom
  %(prog)s --i2c-bus 30 --json
  DECODE_I2C_EEPROM_PATH=/path/to/eeprom %(prog)s --raw
""",
    )
    parser.add_argument("interface", nargs="?", help="SONiC interface e.g. Ethernet16")
    parser.add_argument("--eeprom-path", help="Sysfs EEPROM file path")
    parser.add_argument("--i2c-bus", type=int, help="I2C bus number (sysfs 0x50 EEPROM node)")
    parser.add_argument("--i2c-addr", type=lambda x: int(x, 0), default=0x50, help="I2C addr (default 0x50)")
    parser.add_argument("--json", action="store_true", help="Structured JSON (decoded fields)")
    parser.add_argument("--raw", action="store_true", help="Hex dump only, no decode")
    parser.add_argument("--no-page1", action="store_true", help="Skip upper page 01h read")
    parser.add_argument("--no-page2", action="store_true", help="Skip upper page 02h read")
    parser.add_argument("-v", "--version", action="version", version=__version__)

    args = parser.parse_args(argv)

    if not args.interface and not args.eeprom_path and args.i2c_bus is None:
        parser.error("Provide interface, --eeprom-path, or --i2c-bus")

    try:
        reader, resolved = open_reader(
            interface=args.interface,
            eeprom_path=args.eeprom_path,
            i2c_bus=args.i2c_bus,
            i2c_addr=args.i2c_addr,
        )
    except EepromReadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    meta = {
        "interface": resolved.interface,
        "eeprom_path": resolved.eeprom_path,
        "backend": resolved.backend,
        **resolved.meta,
    }

    try:
        raw = reader.read_all_pages(pages=_build_page_list(args.no_page1, args.no_page2))
    except EepromReadError as e:
        print(f"Read error: {e}", file=sys.stderr)
        print("Tip: upper pages need write access for page select — try sudo", file=sys.stderr)
        return 1

    if args.raw:
        print(f"# {meta}")
        print("LOWER 0-127:")
        print(raw["lower"].hex())
        for p in sorted(raw["upper"].keys()):
            print(f"UPPER page {p:02x}h:")
            print(raw["upper"][p].hex())
        return 0

    ident = raw["lower"][0]

    if args.json:
        print(format_json(_decode(raw), meta))
        return 0

    if _is_qsfp(ident):
        print(format_bytemap_sff8636(raw, meta))
        return 0

    print(format_text(_decode(raw), meta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
