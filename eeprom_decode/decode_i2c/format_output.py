"""Shared formatters and text output for non–byte-map decoders (SFP, unknown)."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def banner(title: str, width: int = 72) -> str:
    line = "=" * width
    pad = " " + title.upper() + " "
    if len(pad) < width - 2:
        side = (width - len(pad)) // 2
        inner = "=" * side + pad + "=" * (width - side - len(pad))
    else:
        inner = pad[:width]
    return f"\n{line}\n{inner}\n{line}\n"


def subheading(title: str) -> str:
    return f"\n  ── {title} ──\n"


def kv(d: Dict[str, Any], indent: int = 1) -> str:
    lines = []
    pad = "  " * indent
    for k, v in d.items():
        if k == "all":
            continue
        if isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(kv(v, indent + 1))
        elif isinstance(v, list):
            if not v:
                lines.append(f"{pad}{k}: (none)")
            else:
                lines.append(f"{pad}{k}:")
                for item in v:
                    if isinstance(item, dict):
                        parts = ", ".join(f"{ik}={iv}" for ik, iv in item.items())
                        lines.append(f"{pad}  {parts}")
                    else:
                        lines.append(f"{pad}  - {item}")
        else:
            lines.append(f"{pad}{k}: {v}")
    return "\n".join(lines)


def fmt_cell(value: Any, width: int, default: str = "—") -> str:
    if value is None:
        return f"{default:>{width}}"
    if isinstance(value, float):
        return f"{value:>{width}.3f}" if width <= 8 else f"{value:>{width}.4f}"
    return f"{value!s:>{width}}"


def lane_table(lanes: List[Dict[str, Any]]) -> str:
    lines = [
        "    Lane   RX (dBm)   TX (dBm)   TX bias (mA)   RX (µW)   TX (µW)",
        "    ----   --------   --------   ------------   -------   -------",
    ]
    for ln in lanes:
        lines.append(
            "    {lane:<4}   {rxdbm}   {txdbm}   {bias}   {rxuw}   {txuw}".format(
                lane=ln.get("lane", "?"),
                rxdbm=fmt_cell(ln.get("rx_power_dbm"), 8),
                txdbm=fmt_cell(ln.get("tx_power_dbm"), 8),
                bias=fmt_cell(ln.get("tx_bias_ma"), 12, default="—"),
                rxuw=fmt_cell(ln.get("rx_power_uw"), 7),
                txuw=fmt_cell(ln.get("tx_power_uw"), 7),
            )
        )
    return "\n".join(lines)


def format_text(decoded: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """Key/value text for SFP (SFF-8472) and unknown identifiers."""
    out = [banner("Access / I2C path"), kv(meta, indent=1), banner(decoded.get("standard", "Decoded"))]
    for key, val in decoded.items():
        if key == "standard":
            continue
        out.append(banner(key.replace("_", " ")))
        if isinstance(val, dict):
            out.append(kv(val, indent=1))
        else:
            out.append(f"  {val}\n")
    return "".join(out)


def format_json(decoded: Dict[str, Any], meta: Dict[str, Any]) -> str:
    return json.dumps({"meta": meta, "decoded": decoded}, indent=2, default=str)


# Back-compat aliases for internal imports
_banner = banner
_subheading = subheading
_kv = kv
_lane_table = lane_table
