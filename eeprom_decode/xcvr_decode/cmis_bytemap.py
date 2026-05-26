"""CMIS field map in strict byte order for human-readable output.

Mirrors sff8636_bytemap.py structure but follows CMIS 4.x/5.x layout.
"""

from __future__ import annotations

import math
import struct
from typing import Any, Callable, Dict, List, Tuple

from . import cmis
from .format_output import banner, kv, subheading
from .sff8636_bytemap import _addr_label

Field = Tuple[int, int, str, Callable[[bytes], str]]
Section = Tuple[str, List[Field]]


def _hex(b: bytes) -> str:
    return b.hex() if b else "(empty)"


def _ascii(b: bytes) -> str:
    return b.decode("ascii", errors="replace").strip() or "(blank)"


def _u16(b: bytes, signed: bool = False) -> int:
    return struct.unpack(">h" if signed else ">H", b)[0]


# ---------------------------------------------------------------------------
# Lower page field decoders
# ---------------------------------------------------------------------------

def _cmis_id(b: bytes) -> str:
    return cmis.CMIS_IDENTIFIERS.get(b[0], f"Unknown (0x{b[0]:02X})")


def _cmis_rev(b: bytes) -> str:
    major = (b[0] >> 4) & 0x0F
    minor = b[0] & 0x0F
    return f"{major}.{minor}"


def _cmis_status(b: bytes) -> str:
    s = b[0]
    flat = bool(s & 0x80)
    intl = bool(s & 0x40)
    state_code = (s >> 1) & 0x07
    state = cmis.MODULE_STATE.get(state_code, f"Unknown({state_code})")
    return f"0x{s:02X} — flat_memory={flat}, IntL={intl}, module_state={state}"


def _cmis_flags(b: bytes) -> str:
    v = b[0]
    if v == 0:
        return "0x00 (no faults)"
    parts = []
    if v & 0x08:
        parts.append("ModStateChanged")
    if v & 0x04:
        parts.append("FW_Fault")
    if v & 0x02:
        parts.append("VendorFault")
    if v & 0x01:
        parts.append("DataPathStateChanged")
    return f"0x{v:02X} — " + ", ".join(parts) if parts else f"0x{v:02X}"


def _cmis_temp(b: bytes) -> str:
    val = _u16(b, signed=True) / 256.0
    if val == 0.0:
        return "0.00 °C (not monitored or passive module)"
    return f"{val:.2f} °C"


def _cmis_voltage(b: bytes) -> str:
    val = _u16(b) * 100e-6
    if val == 0.0:
        return "0.0000 V (not monitored or passive module)"
    return f"{val:.4f} V"


def _tx_power_4lanes(b: bytes) -> str:
    """Decode TX output power for up to 4 lanes (2 bytes each, 0.1µW units)."""
    if all(x == 0 for x in b):
        return "all lanes 0.0 µW (passive or powered down)"
    parts = []
    for i in range(min(4, len(b) // 2)):
        raw = _u16(b[i*2:i*2+2])
        uw = raw * 0.1
        if uw > 0:
            dbm = 10 * math.log10(uw / 1000)
            parts.append(f"L{i+1}={uw:.1f}µW ({dbm:.2f}dBm)")
        else:
            parts.append(f"L{i+1}=0.0µW")
    return ", ".join(parts)


def _tx_bias_4lanes(b: bytes) -> str:
    """Decode TX bias current for up to 4 lanes (2 bytes each, 2µA units)."""
    if all(x == 0 for x in b):
        return "all lanes 0.000 mA (passive or powered down)"
    parts = []
    for i in range(min(4, len(b) // 2)):
        raw = _u16(b[i*2:i*2+2])
        ma = raw * 0.002
        parts.append(f"L{i+1}={ma:.3f}mA")
    return ", ".join(parts)


def _rx_power_4lanes(b: bytes) -> str:
    """Decode RX input power for up to 4 lanes (2 bytes each, 0.1µW units)."""
    if all(x == 0 for x in b):
        return "all lanes 0.0 µW (passive or powered down)"
    parts = []
    for i in range(min(4, len(b) // 2)):
        raw = _u16(b[i*2:i*2+2])
        uw = raw * 0.1
        if uw > 0:
            dbm = 10 * math.log10(uw / 1000)
            parts.append(f"L{i+1}={uw:.1f}µW ({dbm:.2f}dBm)")
        else:
            parts.append(f"L{i+1}=0.0µW")
    return ", ".join(parts)


def _media_type(b: bytes) -> str:
    return cmis.MEDIA_TYPE.get(b[0], f"Unknown (0x{b[0]:02X})")


def _app_advertising_block(b: bytes) -> str:
    """Decode up to 10 application advertising entries from 40 bytes."""
    media_type = 0x03  # default copper; actual media type from byte 85 passed separately
    lines = []
    for i in range(10):
        offset = i * 4
        if offset + 4 > len(b):
            break
        host_id = b[offset]
        media_id = b[offset + 1]
        lanes = b[offset + 2]
        assign = b[offset + 3]
        if host_id == 0 and media_id == 0:
            break
        host_lane_count = (lanes >> 4) & 0x0F
        media_lane_count = lanes & 0x0F
        host_name = cmis.HOST_INTERFACE_ID.get(host_id, f"0x{host_id:02X}")
        media_name = cmis.COPPER_MEDIA_INTERFACE_ID.get(media_id, f"0x{media_id:02X}")
        lines.append(
            f"App {i+1}: {host_name} | "
            f"Host×{host_lane_count} Media×{media_lane_count} | "
            f"Assign=0x{assign:02X} | "
            f"Media={media_name}"
        )
    if not lines:
        return "(none)"
    return "\n                    ".join(lines)


# ---------------------------------------------------------------------------
# Upper page 00h field decoders
# ---------------------------------------------------------------------------

def _vendor_oui(b: bytes) -> str:
    return "-".join(f"{x:02x}" for x in b)


def _connector(b: bytes) -> str:
    return cmis.CONNECTOR_TYPE.get(b[0], f"Unknown (0x{b[0]:02X})")


def _cable_length(b: bytes) -> str:
    length = cmis.decode_cable_length(b[0])
    if length == 0.0:
        return "0 (not a cable assembly)"
    return f"{length:.1f} m"


def _power_class(b: bytes) -> str:
    pwr_class, desc = cmis.decode_power_class(b[0])
    return f"Power Class {pwr_class} ({desc} max)"


def _max_power(b: bytes) -> str:
    w = cmis.decode_max_power(b[0])
    return f"{w:.2f} W" if w > 0 else "N/A (0)"


def _media_interface_tech(b: bytes) -> str:
    return cmis.MEDIA_INTERFACE_TECH.get(b[0], f"Unknown (0x{b[0]:02X})")


def _firmware_version(b: bytes) -> str:
    """Decode firmware version (2 bytes: major.minor)."""
    if len(b) >= 2:
        if b[0] == 0 and b[1] == 0:
            return "N/A (passive module or not programmed)"
        return f"{b[0]}.{b[1]}"
    return f"0x{b[0]:02X}"


def _module_controls(b: bytes) -> str:
    """Decode module-level control bits."""
    if len(b) < 1:
        return _hex(b)
    ctrl = b[0]
    parts = []
    if ctrl & 0x10:
        parts.append("LowPwrRequestSW")
    if ctrl & 0x08:
        parts.append("ForceLowPwr")
    if ctrl & 0x04:
        parts.append("SWReset")
    if not parts:
        return f"0x{ctrl:02X} (normal operation)"
    return f"0x{ctrl:02X} — " + ", ".join(parts)


def _cc_byte(b: bytes) -> str:
    return f"0x{b[0]:02X}"


def _date_code(b: bytes) -> str:
    s = _ascii(b)
    if len(s) >= 6 and s[:6].isdigit():
        formatted = f"20{s[0:2]}-{s[2:4]}-{s[4:6]}"
        lot = s[6:].strip()
        if lot:
            return f"{s} → {formatted} (lot: {lot})"
        return f"{s} → {formatted}"
    return s


# ---------------------------------------------------------------------------
# Section definitions
# ---------------------------------------------------------------------------

LOWER_PAGE_SECTIONS: List[Section] = [
    ("Module identity", [
        (0, 1, "Identifier", _cmis_id),
        (1, 2, "CMIS Revision", _cmis_rev),
    ]),
    ("Module status", [
        (2, 3, "Status/Control", _cmis_status),
        (3, 4, "Module-level flags", _cmis_flags),
        (4, 9, "Module fault/status flags (bytes 4–8)", _hex),
        (9, 14, "Lane/DataPath status (bytes 9–13)", _hex),
    ]),
    ("Module monitors (live telemetry)", [
        (14, 16, "Module temperature", _cmis_temp),
        (16, 18, "Supply voltage (Vcc)", _cmis_voltage),
        (18, 20, "Reserved (bytes 18–19)", _hex),
        (20, 22, "Aux monitor 1 (bytes 20–21)", _hex),
        (22, 24, "Aux monitor 2 (bytes 22–23)", _hex),
        (24, 26, "Custom monitor (bytes 24–25)", _hex),
    ]),
    ("Lane monitors (live per-lane telemetry)", [
        (26, 34, "TX output power lanes 1–4", _tx_power_4lanes),
        (34, 39, "TX bias current (bytes 34–38)", _tx_bias_4lanes),
    ]),
    ("Firmware version", [
        (39, 41, "Active Firmware Version", _firmware_version),
        (41, 43, "Inactive Firmware Version", _firmware_version),
    ]),
    ("Lane monitors (continued)", [
        (43, 50, "RX input power (bytes 43–49)", _rx_power_4lanes),
        (50, 78, "Extended lane monitors / reserved (bytes 50–77)", _hex),
    ]),
    ("Module controls & active application", [
        (78, 79, "Module-level control", _module_controls),
        (79, 85, "DataPath/lane controls (bytes 79–84)", _hex),
        (85, 86, "Media Type", _media_type),
    ]),
    ("Application Advertising", [
        (86, 126, "Applications (bytes 86–125)", _app_advertising_block),
        (126, 128, "Reserved (bytes 126–127)", _hex),
    ]),
]

PAGE_00_SECTIONS: List[Section] = [
    ("Module identification", [
        (128, 129, "Identifier", _cmis_id),
        (129, 145, "Vendor Name", _ascii),
        (145, 148, "Vendor OUI", _vendor_oui),
        (148, 164, "Vendor Part Number", _ascii),
        (164, 166, "Module Hardware Revision", _ascii),
        (166, 182, "Vendor Serial Number", _ascii),
        (182, 190, "Date Code", _date_code),
    ]),
    ("Checksums & CLEI", [
        (190, 191, "CLEI code present / lot", _hex),
        (191, 192, "CC_BASE checksum", _cc_byte),
        (192, 200, "CLEI code (bytes 192–199)", _hex),
    ]),
    ("Power & physical", [
        (200, 201, "Module Power Characteristics", _power_class),
        (201, 202, "Max Power Dissipation", _max_power),
        (202, 203, "Cable Assembly Length", _cable_length),
        (203, 204, "Connector Type", _connector),
    ]),
    ("Module properties", [
        (204, 211, "Reserved / module info (bytes 204–210)", _hex),
        (211, 212, "Media Interface Technology", _media_interface_tech),
        (212, 222, "Reserved (bytes 212–221)", _hex),
        (222, 223, "CC_EXT checksum", _cc_byte),
        (223, 256, "Vendor specific (bytes 223–255)", _hex),
    ]),
]


# ---------------------------------------------------------------------------
# Page rendering (reuse logic from sff8636_bytemap)
# ---------------------------------------------------------------------------

def _render_fields(
    data: bytes, base_addr: int, fields: List[Field], pos: int = 0
) -> Tuple[List[str], int]:
    lines: List[str] = []
    for start, end, name, decode_fn in fields:
        rel_start = start - base_addr
        rel_end = end - base_addr
        if rel_start < 0:
            continue
        if rel_start >= len(data):
            break
        rel_end = min(rel_end, len(data))
        if rel_start > pos:
            gap = data[pos:rel_start]
            lines.append(
                f"  {_addr_label(base_addr + pos, base_addr + rel_start)}  "
                f"** Reserved **  {gap.hex() or '(empty)'}\n"
            )
        chunk = data[rel_start:rel_end]
        try:
            value = decode_fn(chunk)
        except Exception as e:
            value = f"<decode error: {e}> raw={chunk.hex()}"
        if "\n" in value:
            lines.append(f"  {_addr_label(start, end)}  {name}:\n                    {value}\n")
        else:
            lines.append(f"  {_addr_label(start, end)}  {name}: {value}\n")
        pos = rel_end
    return lines, pos


def render_page_sections(data: bytes, base_addr: int, sections: List[Section]) -> List[str]:
    lines: List[str] = []
    pos = 0
    for title, fields in sections:
        lines.append(subheading(title))
        section_lines, pos = _render_fields(data, base_addr, fields, pos)
        lines.extend(section_lines)
    if pos < len(data):
        gap = data[pos:]
        lines.append(
            f"  {_addr_label(base_addr + pos, base_addr + len(data))}  "
            f"** Reserved **  {gap.hex()}\n"
        )
    return lines


# ---------------------------------------------------------------------------
# Main bytemap formatter
# ---------------------------------------------------------------------------

def format_bytemap_cmis(raw: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """Render full CMIS EEPROM decode in human-readable byte-map format."""
    out: List[str] = []
    out.append(banner("Access / I2C path"))
    out.append(kv(meta, indent=1))
    out.append(banner("CMIS EEPROM decode"))
    out.append(
        "  CMIS (Common Management Interface Specification) module.\n"
        "  Lower page 0–127 (always accessible); upper page 00h 128–255.\n"
        "  Flat memory modules have no page select (passive copper DACs, etc).\n"
    )

    lower = raw["lower"]
    upper = raw["upper"]

    out.append(banner("Lower page  bytes 0–127"))
    out.extend(render_page_sections(lower, 0, LOWER_PAGE_SECTIONS))

    if 0 in upper:
        out.append(banner("Upper page 00h  bytes 128–255"))
        out.extend(render_page_sections(upper[0], 128, PAGE_00_SECTIONS))

    return "".join(out)
