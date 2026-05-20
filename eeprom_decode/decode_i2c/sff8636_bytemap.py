"""SFF-8636 field map in strict increasing byte order (SFF-8636 Rev 2.x / qsfp.h)."""

from __future__ import annotations

import math
import struct
from typing import Callable, List, Tuple

from . import codes
from . import sff8636_flags as flags

# (start_byte, end_byte_exclusive, name, decoder)
# decoder receives bytes slice for that range
Field = Tuple[int, int, str, Callable[[bytes], str]]


def _hex(b: bytes) -> str:
    return b.hex() if b else "(empty)"


def _ascii(b: bytes) -> str:
    return b.decode("ascii", errors="replace").strip() or "(blank)"


def _u16(b: bytes, signed: bool = False) -> int:
    return struct.unpack(">h" if signed else ">H", b)[0]


def _id(b: bytes) -> str:
    return codes.IDENTIFIER.get(b[0], f"0x{b[0]:02X}")


def _rev(b: bytes) -> str:
    return codes.REV_COMPLIANCE.get(b[0], f"0x{b[0]:02X}")


def _status(b: bytes) -> str:
    s = b[0]
    return (
        f"0x{s:02X} — DNR={bool(s&1)} IntL_asserted={bool(s&2)} "
        f"flat/page3bit={bool(s&4)}"
    )


def _flag_byte_3(b: bytes) -> str:
    v = b[0]
    parts = []
    if v & 0x0F:
        parts.append(f"RX LOS lanes 1-4: 0x{v&0x0F:x}")
    if v & 0xF0:
        parts.append(f"TX LOS lanes 1-4: 0x{(v>>4)&0xF:x}")
    return " | ".join(parts) if parts else "no LOS flags"


def _flag_byte_4(b: bytes) -> str:
    v = b[0]
    active = [f"TX{i+1}_fault" for i in range(4) if v & (1 << i)]
    return ", ".join(active) if active else "no TX fault"


def _flag_byte_6(b: bytes) -> str:
    v = b[0]
    names = []
    if v & 0x80:
        names.append("temp_high_alarm")
    if v & 0x40:
        names.append("temp_low_alarm")
    if v & 0x20:
        names.append("temp_high_warning")
    if v & 0x10:
        names.append("temp_low_warning")
    return ", ".join(names) if names else f"0x{v:02X} (none)"


def _flag_byte_7(b: bytes) -> str:
    v = b[0]
    names = []
    if v & 0x80:
        names.append("vcc_high_alarm")
    if v & 0x40:
        names.append("vcc_low_alarm")
    if v & 0x20:
        names.append("vcc_high_warning")
    if v & 0x10:
        names.append("vcc_low_warning")
    return ", ".join(names) if names else f"0x{v:02X} (none)"


def _flag_rx_pwr_12(b: bytes) -> str:
    return _decode_nibble_flags(b[0], "RX power lanes 1-2")


def _flag_rx_pwr_34(b: bytes) -> str:
    return _decode_nibble_flags(b[0], "RX power lanes 3-4")


def _flag_tx_bias_12(b: bytes) -> str:
    return _decode_nibble_flags(b[0], "TX bias lanes 1-2")


def _flag_tx_bias_34(b: bytes) -> str:
    return _decode_nibble_flags(b[0], "TX bias lanes 3-4")


def _flag_tx_pwr_12(b: bytes) -> str:
    return _decode_nibble_flags(b[0], "TX power lanes 1-2")


def _flag_tx_pwr_34(b: bytes) -> str:
    return _decode_nibble_flags(b[0], "TX power lanes 3-4")


def _decode_nibble_flags(v: int, label: str) -> str:
    if v == 0:
        return "none"
    return f"0x{v:02X}"


def _temp_live(b: bytes) -> str:
    return f"{_u16(b, signed=True) / 256.0:.4f} °C"


def _vcc_live(b: bytes) -> str:
    return f"{_u16(b) * 1e-4:.4f} V"


def _rx_uw(b: bytes) -> str:
    uw = _u16(b) * 0.1
    dbm = 10 * __import__("math").log10(uw / 1000) if uw > 0 else float("-inf")
    return f"{uw:.2f} µW ({dbm:.3f} dBm)"


def _tx_bias_ma(b: bytes) -> str:
    return f"{_u16(b) * 2e-3:.4f} mA"


def _tx_uw(b: bytes) -> str:
    return _rx_uw(b)


def _tx_disable(b: bytes) -> str:
    d = flags.decode_tx_disable(b[0])
    return ", ".join(f"{k}={v}" for k, v in d.items())


def _rate_sel(b: bytes) -> str:
    d = flags.decode_rate_select(b[0])
    return ", ".join(f"lane{n}={d[f'lane{n}']}" for n in range(1, 5))


def _pwr_ctrl(b: bytes) -> str:
    d = flags.decode_power_control(b[0])
    return ", ".join(f"{k}={v}" for k, v in d.items())


def _page_sel(b: bytes) -> str:
    return f"0x{b[0]:02X} ({b[0]})"


def _eth_comp(b: bytes) -> str:
    return codes.decode_bitmask_str(b[0], codes.ETH_10G_40G)


def _bit_comp(b: bytes, table: dict, name: str) -> str:
    return codes.decode_bitmask_str(b[0], table)


def _ext_id(b: bytes) -> str:
    x = b[0]
    pwr = (x >> 6) & 3
    return (
        f"0x{x:02X} — class {pwr+1}, CLEI={bool(x&0x10)}, "
        f"CDR_TX={bool(x&0x08)}, CDR_RX={bool(x&0x04)}"
    )


def _wl_nm(b: bytes) -> str:
    return f"{_u16(b) / 20.0:.2f} nm"


def _wl_tol(b: bytes) -> str:
    return f"{_u16(b) / 200.0:.3f} nm"


def _threshold_temp(b: bytes) -> str:
    return f"{_u16(b, signed=True) / 256.0:.4f} °C"


def _threshold_v(b: bytes) -> str:
    return f"{_u16(b) / 10000.0:.4f} V"


def _threshold_bias(b: bytes) -> str:
    return f"{_u16(b) / 500.0:.4f} mA"


def _threshold_pwr_dbm(b: bytes) -> str:
    raw = _u16(b)
    if raw in (0, 0xFFFF):
        return "N/A"
    mw = raw / 10000.0
    return f"{10 * math.log10(mw):.3f} dBm (raw={raw})"


def _diag_type(b: bytes) -> str:
    d = b[0]
    return (
        f"0x{d:02X} — temp={bool(d&0x20)} vcc={bool(d&0x10)} "
        f"OMA={bool(d&0x08)} tx_pwr={bool(d&0x04)} "
        f"tx_bias={bool(d&0x02)} rx_pwr={bool(d&0x01)}"
    )


def _date(b: bytes) -> str:
    s = _ascii(b)
    if len(s) >= 6 and s[:6].isdigit():
        return f"{s} → 20{s[0:2]}-{s[2:4]}-{s[4:6]}"
    return s


# Section = (subheading title, fields in byte order within section)
Section = Tuple[str, List[Field]]


LOWER_PAGE_SECTIONS: List[Section] = [
    ("Module identity", [
        (0, 1, "Identifier", _id),
        (1, 2, "Revision compliance", _rev),
    ]),
    ("Status", [
        (2, 3, "Status", _status),
    ]),
    ("Alarm & warning flags", [
        (3, 4, "Channel status / LOS (byte 3)", _flag_byte_3),
        (4, 5, "TX fault (byte 4)", _flag_byte_4),
        (5, 6, "Reserved / vendor (byte 5)", _hex),
        (6, 7, "Module alarm/warning — temperature (byte 6)", _flag_byte_6),
        (7, 8, "Module alarm/warning — Vcc (byte 7)", _flag_byte_7),
        (8, 9, "Vendor specific (byte 8)", _hex),
        (9, 10, "Channel alarm/warning — RX power lanes 1–2", _flag_rx_pwr_12),
        (10, 11, "Channel alarm/warning — RX power lanes 3–4", _flag_rx_pwr_34),
        (11, 12, "Channel alarm/warning — TX bias lanes 1–2", _flag_tx_bias_12),
        (12, 13, "Channel alarm/warning — TX bias lanes 3–4", _flag_tx_bias_34),
        (13, 14, "Channel alarm/warning — TX power lanes 1–2", _flag_tx_pwr_12),
        (14, 15, "Channel alarm/warning — TX power lanes 3–4", _flag_tx_pwr_34),
        (15, 22, "Reserved / vendor (bytes 15–21)", _hex),
    ]),
    ("Module monitors (live DOM)", [
        (22, 24, "Module temperature", _temp_live),
        (24, 26, "Reserved (bytes 24–25)", _hex),
        (26, 28, "Supply voltage Vcc", _vcc_live),
    ]),
    ("Channel monitors (per lane)", [
        (28, 34, "Reserved (bytes 28–33)", _hex),
        (34, 36, "RX1 power", _rx_uw),
        (36, 38, "RX2 power", _rx_uw),
        (38, 40, "RX3 power", _rx_uw),
        (40, 42, "RX4 power", _rx_uw),
        (42, 44, "TX1 bias", _tx_bias_ma),
        (44, 46, "TX2 bias", _tx_bias_ma),
        (46, 48, "TX3 bias", _tx_bias_ma),
        (48, 50, "TX4 bias", _tx_bias_ma),
        (50, 52, "TX1 power", _tx_uw),
        (52, 54, "TX2 power", _tx_uw),
        (54, 56, "TX3 power", _tx_uw),
        (56, 58, "TX4 power", _tx_uw),
    ]),
    ("Controls", [
        (58, 86, "Reserved (bytes 58–85)", _hex),
        (86, 87, "TX Disable", _tx_disable),
        (87, 88, "RX Rate Select", _rate_sel),
        (88, 89, "TX Rate Select", _rate_sel),
        (89, 93, "Reserved (bytes 89–92)", _hex),
        (93, 94, "Power Control", _pwr_ctrl),
    ]),
    ("Page select & reserved", [
        (94, 127, "Reserved (bytes 94–126)", _hex),
        (127, 128, "Page Select", _page_sel),
    ]),
]

PAGE_00_SECTIONS: List[Section] = [
    ("Module type & connector", [
        (128, 129, "Identifier", _id),
        (129, 130, "Extended identifier", _ext_id),
        (130, 131, "Connector type", lambda b: codes.CONNECTOR.get(b[0], f"0x{b[0]:02X}")),
    ]),
    ("Specification compliance", [
        (131, 132, "10/40G Ethernet compliance", _eth_comp),
        (132, 133, "SONET compliance", lambda b: _bit_comp(b, codes.SONET, "SONET")),
        (133, 134, "SAS/SATA compliance", lambda b: _bit_comp(b, codes.SAS_SATA, "SAS/SATA")),
        (134, 135, "Gigabit Ethernet compliance", lambda b: _bit_comp(b, codes.GBE, "GbE")),
        (135, 137, "Fibre Channel link length / transmitter tech (bytes 135–136)", _hex),
        (137, 138, "Fibre Channel transmission media", lambda b: _bit_comp(b, codes.FC_MEDIA, "FC media")),
        (138, 139, "Fibre Channel speed", lambda b: _bit_comp(b, codes.FC_SPEED, "FC speed")),
    ]),
    ("Reach & device technology", [
        (139, 140, "Encoding", lambda b: codes.ENCODING.get(b[0], f"0x{b[0]:02X}")),
        (140, 141, "Nominal bit rate (100 Mb/s)", lambda b: f"{b[0]} (255=see ext. compliance)" if b[0] == 255 else str(b[0])),
        (141, 142, "Extended rate select compliance", lambda b: codes.EXT_RATESELECT.get(b[0], f"0x{b[0]:02X}")),
        (142, 143, "Length (SMF, km)", lambda b: str(b[0])),
        (143, 144, "Length (OM3, 2m)", lambda b: str(b[0])),
        (144, 145, "Length (OM2, 1m)", lambda b: str(b[0])),
        (145, 146, "Length (OM1, 1m)", lambda b: str(b[0])),
        (146, 147, "Length (copper or OM4, 1m)", lambda b: str(b[0])),
        (147, 148, "Device technology", _hex),
    ]),
    ("Vendor identification", [
        (148, 164, "Vendor name (ASCII)", _ascii),
        (164, 165, "Extended module codes (byte 164)", lambda b: codes.EXT_MODULE_CODES.get(b[0], f"0x{b[0]:02X}")),
        (165, 168, "Vendor OUI", _hex),
        (168, 184, "Vendor part number (ASCII)", _ascii),
        (184, 186, "Vendor revision (ASCII)", _ascii),
        (186, 188, "Wavelength", _wl_nm),
        (188, 190, "Wavelength tolerance", _wl_tol),
        (190, 191, "Max case temperature", lambda b: f"{b[0]} °C"),
        (191, 192, "CC_BASE checksum", _hex),
        (192, 193, "Extended specification compliance (byte 192)", lambda b: codes.EXT_SPEC_COMPLIANCE.get(b[0], f"0x{b[0]:02X}")),
        (193, 194, "Options (byte 193)", _hex),
        (194, 195, "Options (byte 194)", _hex),
        (195, 196, "Options (byte 195)", _hex),
    ]),
    ("Options & diagnostic capabilities", [
        (196, 212, "Vendor serial number (ASCII)", _ascii),
        (212, 220, "Vendor date code (ASCII)", _date),
        (220, 221, "Diagnostic monitoring type", _diag_type),
        (221, 223, "Enhanced options / reserved", _hex),
        (223, 224, "CC_EXT checksum", _hex),
    ]),
    ("Vendor-specific", [
        (224, 256, "Vendor specific (bytes 224–255)", _hex),
    ]),
]

PAGE_03_SECTIONS: List[Section] = [
    ("Temperature thresholds", [
        (128, 130, "Temp high alarm", _threshold_temp),
        (130, 132, "Temp low alarm", _threshold_temp),
        (132, 134, "Temp high warning", _threshold_temp),
        (134, 136, "Temp low warning", _threshold_temp),
        (136, 144, "Reserved", _hex),
    ]),
    ("Vcc thresholds", [
        (144, 146, "Vcc high alarm", _threshold_v),
        (146, 148, "Vcc low alarm", _threshold_v),
        (148, 150, "Vcc high warning", _threshold_v),
        (150, 152, "Vcc low warning", _threshold_v),
        (152, 176, "Reserved", _hex),
    ]),
    ("RX power thresholds", [
        (176, 178, "RX power high alarm", _threshold_pwr_dbm),
        (178, 180, "RX power low alarm", _threshold_pwr_dbm),
        (180, 182, "RX power high warning", _threshold_pwr_dbm),
        (182, 184, "RX power low warning", _threshold_pwr_dbm),
    ]),
    ("TX bias thresholds", [
        (184, 186, "TX bias high alarm", _threshold_bias),
        (186, 188, "TX bias low alarm", _threshold_bias),
        (188, 190, "TX bias high warning", _threshold_bias),
        (190, 192, "TX bias low warning", _threshold_bias),
    ]),
    ("TX power thresholds", [
        (192, 194, "TX power high alarm", _threshold_pwr_dbm),
        (194, 196, "TX power low alarm", _threshold_pwr_dbm),
        (196, 198, "TX power high warning", _threshold_pwr_dbm),
        (198, 200, "TX power low warning", _threshold_pwr_dbm),
        (200, 256, "Reserved / vendor-specific", _hex),
    ]),
]

def _addr_label(start: int, end: int) -> str:
    last = end - 1
    if end - start == 1:
        return f"[{start:3d}]     "
    return f"[{start:3d}-{last:3d}]"


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
        lines.append(f"  {_addr_label(start, end)}  {name}: {value}\n")
        pos = rel_end
    return lines, pos


_CHANNEL_MONITORS_SECTION = "Channel monitors (per lane)"


def render_page_sections(data: bytes, base_addr: int, sections: List[Section]) -> List[str]:
    from .format_output import lane_table, subheading
    from .sff8636 import parse_channel_lanes

    lines: List[str] = []
    pos = 0
    for title, fields in sections:
        lines.append(subheading(title))
        section_lines, pos = _render_fields(data, base_addr, fields, pos)
        lines.extend(section_lines)
        if title == _CHANNEL_MONITORS_SECTION and base_addr == 0:
            lanes = parse_channel_lanes(data)
            if lanes:
                lines.append("\n")
                lines.append(lane_table(lanes))
                lines.append("\n")
    if pos < len(data):
        gap = data[pos:]
        lines.append(
            f"  {_addr_label(base_addr + pos, base_addr + len(data))}  "
            f"** Reserved **  {gap.hex()}\n"
        )
    return lines
