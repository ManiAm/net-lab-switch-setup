"""SFF-8636 text output: EEPROM bytes in address order with decoded fields."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from .format_output import banner, kv, subheading
from .sff8636 import (
    decode_upper_page_01,
    decode_upper_page_02,
    summarize_page_01,
    summarize_page_02,
)
from .sff8636_bytemap import (
    LOWER_PAGE_SECTIONS,
    PAGE_00_SECTIONS,
    PAGE_03_SECTIONS,
    render_page_sections,
)


def _render_raw_lines(data: bytes, base: int) -> List[str]:
    lines: List[str] = []
    i = 0
    while i < len(data):
        end = min(i + 16, len(data))
        chunk = data[i:end]
        a0, a1 = base + i, base + end - 1
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  [{a0:3d}-{a1:3d}]  hex {chunk.hex():<32}  |{asc}|\n")
        i = end
    return lines


def _render_hex_with_summary(
    data: bytes,
    base: int,
    decode_fn: Callable[[bytes], Dict[str, Any]],
    summary_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> List[str]:
    lines = _render_raw_lines(data, base)
    decoded = decode_fn(data)
    lines.append(subheading("Decoded summary"))
    lines.append(kv(summary_fn(decoded), indent=2))
    lines.append("\n")
    return lines


def format_bytemap_sff8636(raw: Dict[str, Any], meta: Dict[str, Any]) -> str:
    out: List[str] = []
    out.append(banner("Access / I2C path"))
    out.append(kv(meta, indent=1))
    out.append(banner("SFF-8636 EEPROM decode"))
    out.append(
        "  Byte addresses are offsets on I2C A0h (0x50). Lower page 0–127; "
        "upper 128–255 per page select.\n"
        "  Unmapped bytes appear as ** Reserved ** with hex.\n"
    )

    lower = raw["lower"]
    upper = raw["upper"]

    out.append(banner("Lower page  bytes 0–127"))
    out.extend(render_page_sections(lower, 0, LOWER_PAGE_SECTIONS))

    if 0 in upper:
        out.append(banner("Upper page 00h  bytes 128–255  (page select = 00h)"))
        out.extend(render_page_sections(upper[0], 128, PAGE_00_SECTIONS))

    if 1 in upper:
        out.append(banner("Upper page 01h  bytes 128–255  (page select = 01h)"))
        out.extend(
            _render_hex_with_summary(upper[1], 128, decode_upper_page_01, summarize_page_01)
        )

    if 2 in upper:
        out.append(banner("Upper page 02h  bytes 128–255  (page select = 02h)"))
        out.extend(
            _render_hex_with_summary(upper[2], 128, decode_upper_page_02, summarize_page_02)
        )

    if 3 in upper:
        out.append(banner("Upper page 03h  bytes 128–255  (page select = 03h)"))
        out.extend(render_page_sections(upper[3], 128, PAGE_03_SECTIONS))

    return "".join(out)
