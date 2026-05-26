"""CMIS (Common Management Interface Specification) decoder.

Covers CMIS 4.x / 5.x modules: QSFP-DD (0x18), OSFP-8X (0x19), OSFP (0x1E).
Independent implementation — does not rely on SONiC or vendor libraries.

Reference: CMIS Rev 5.2 / SFF-8024 Rev 4.11
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Identifier codes (SFF-8024 Table 4-1)
# ---------------------------------------------------------------------------
CMIS_IDENTIFIERS = {
    0x18: "QSFP-DD Double Density 8X Pluggable Transceiver",
    0x19: "OSFP 8X Pluggable Transceiver",
    0x1E: "OSFP",
}

# ---------------------------------------------------------------------------
# Connector type (SFF-8024 Table 4-3)
# ---------------------------------------------------------------------------
CONNECTOR_TYPE = {
    0x00: "Unknown or unspecified",
    0x01: "SC (Subscriber Connector)",
    0x02: "Fibre Channel Style 1 copper",
    0x03: "Fibre Channel Style 2 copper",
    0x04: "BNC/TNC",
    0x05: "Fibre Channel coax headers",
    0x06: "Fiber Jack",
    0x07: "LC (Lucent Connector)",
    0x08: "MT-RJ",
    0x09: "MU",
    0x0A: "SG",
    0x0B: "Optical pigtail",
    0x0C: "MPO 1x12",
    0x0D: "MPO 2x16",
    0x20: "HSSDC II",
    0x21: "Copper pigtail",
    0x22: "RJ45",
    0x23: "No separable connector",
    0x24: "MXC 2x16",
    0x25: "CS optical connector",
    0x26: "SN optical connector",
    0x27: "MPO 2x12",
    0x28: "MPO 1x16",
}

# ---------------------------------------------------------------------------
# Media Type (CMIS byte 85 of lower page)
# ---------------------------------------------------------------------------
MEDIA_TYPE = {
    0x00: "Undefined",
    0x01: "Optical interface — SMF",
    0x02: "Optical interface — MMF",
    0x03: "Passive copper cable",
    0x04: "Active cable",
    0x05: "Base-T",
}

# ---------------------------------------------------------------------------
# Media Interface Technology (upper page 00h byte 210)
# ---------------------------------------------------------------------------
MEDIA_INTERFACE_TECH = {
    0x00: "Undefined",
    0x01: "850 nm VCSEL",
    0x02: "Copper cable unequalized",
    0x03: "Copper cable passive equalized",
    0x04: "Copper cable near and far end limiting active equalizers",
    0x05: "Copper cable far end limiting active equalizers",
    0x06: "Copper cable near end limiting active equalizers",
    0x07: "Copper cable linear active equalizers",
    0x08: "1310 nm VCSEL",
    0x09: "1550 nm VCSEL",
    0x0A: "1310 nm FP",
    0x0B: "1310 nm DFB",
    0x0C: "1550 nm DFB",
    0x0D: "1310 nm EML",
    0x0E: "1550 nm EML",
    0x0F: "Others / undefined",
    0x10: "1490 nm DFB",
    0x11: "Copper cable unequalized (retimed)",
}

# ---------------------------------------------------------------------------
# Host Electrical Interface ID (SFF-8024 Table 4-7, partial)
# ---------------------------------------------------------------------------
HOST_INTERFACE_ID = {
    0x01: "1000BASE-CX (Clause 39)",
    0x02: "XAUI (Clause 47)",
    0x03: "XFI (SFF INF-8071i)",
    0x04: "SFI (SFF-8431)",
    0x05: "25GAUI C2M (Annex 109B)",
    0x06: "XLAUI C2M (Annex 83B)",
    0x07: "XLPPI (Annex 86A)",
    0x08: "LAUI-2 C2M (Annex 135C)",
    0x09: "50GAUI-2 C2M (Annex 135C)",
    0x0A: "50GAUI-1 C2M (Annex 135C)",
    0x0B: "CAUI-4 C2M (Annex 83E)",
    0x0C: "100GAUI-4 C2M (Annex 135E)",
    0x0D: "100GAUI-2 C2M (Annex 135G)",
    0x0E: "200GAUI-8 C2M (Annex 120C)",
    0x0F: "200GAUI-4 C2M (Annex 120E)",
    0x10: "400GAUI-16 C2M (Annex 120C)",
    0x11: "400GAUI-8 C2M (Annex 120E)",
    0x12: "100GAUI-1-S C2M (802.3ck Annex 120G)",
    0x13: "100GAUI-1-L C2M (802.3ck Annex 120G)",
    0x14: "200GAUI-2 C2M",
    0x15: "400GAUI-4 C2M",
    0x16: "800GAUI-8 C2M",
    0x17: "100GAUI-2 C2M (Annex 136D)",
    0x18: "200GAUI-4 C2M (Annex 136E)",
    0x19: "400GAUI-8 C2M (Annex 136F)",
    0x1A: "100GBASE-CR4 (Clause 92)",
    0x1B: "100GBASE-CR2 (Clause 136)",
    0x1C: "200GBASE-CR4 (Clause 136)",
    0x1D: "400G CR8",
    0x1E: "50GBASE-CR (Clause 136)",
    0x1F: "CAUI-4 C2M without FEC",
    0x30: "IB SDR",
    0x31: "IB HDR (Arch.Spec.Vol.2)",
    0x32: "IB NDR",
    0x33: "IB XDR",
    0x40: "10GBASE-KR (Clause 72)",
    0x41: "25GBASE-KR/CR (Clause 91/92)",
    0x42: "40GBASE-KR4/CR4 (Clause 73/92)",
    0x43: "50GBASE-KR/CR (Clause 136)",
    0x44: "100GBASE-KR2/CR2 (Clause 136)",
    0x45: "100GBASE-KR4/CR4 (Clause 73/92)",
    0x46: "100GBASE-CR1 (Clause 162)",
    0x47: "200GBASE-CR2 (Clause 162)",
    0x48: "400GBASE-CR4 (Clause 162)",
    0x49: "800G-ETC-CR8",
    0x4A: "200GBASE-CR1 (Clause 162)",
    0x4B: "400GBASE-CR2",
    0x4C: "800GBASE-CR4",
    0x4D: "1.6TBASE-CR8",
}

# ---------------------------------------------------------------------------
# Media Interface ID for passive copper (media type 0x03)
# ---------------------------------------------------------------------------
COPPER_MEDIA_INTERFACE_ID = {
    0x00: "Undefined",
    0x01: "Copper cable — unequalized",
    0x02: "Copper cable — passive equalized",
    0x03: "Copper cable — active equalized",
    0x04: "Copper cable — near end retimed",
    0x05: "Copper cable — far end retimed",
    0x06: "Copper cable — near and far end retimed",
    0x07: "Copper cable — linear active equalized",
}

# ---------------------------------------------------------------------------
# Module State (lower page byte 2, bits 3:1)
# ---------------------------------------------------------------------------
MODULE_STATE = {
    0: "ModuleResetAsserted (or low power passive)",
    1: "ModuleLowPwr",
    2: "ModulePwrUp",
    3: "ModuleReady",
    4: "ModulePwrDn",
    5: "ModuleFault",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _u16(buf: bytes, signed: bool = False) -> int:
    return struct.unpack(">h" if signed else ">H", buf)[0]


def _ascii(buf: bytes) -> str:
    return buf.decode("ascii", errors="replace").strip()


def _format_date(raw: bytes) -> str:
    s = _ascii(raw)
    if len(s) >= 6 and s[:6].isdigit():
        return f"20{s[0:2]}-{s[2:4]}-{s[4:6]}"
    return s


def decode_cable_length(b: int) -> float:
    """CMIS cable assembly length encoding: bits 7:6=multiplier, 5:0=mantissa."""
    multiplier_table = {0: 0.1, 1: 1.0, 2: 10.0, 3: 0.0}
    mult_code = (b >> 6) & 0x03
    mantissa = b & 0x3F
    mult = multiplier_table.get(mult_code, 0.0)
    if mult_code == 3:
        return 0.0
    return mantissa * mult


def decode_max_power(b: int) -> float:
    """Max power in watts (units of 0.25W per CMIS)."""
    return b * 0.25


def decode_power_class(b: int) -> Tuple[int, str]:
    """Byte 200 bits 7:5 = power class encoding."""
    pwr_class = ((b >> 5) & 0x07) + 1
    max_vals = {1: "1.5W", 2: "3.5W", 3: "7.0W", 4: "10.0W",
                5: "12.0W", 6: "14.0W", 7: "16.0W", 8: "custom"}
    return pwr_class, max_vals.get(pwr_class, "unknown")


# ---------------------------------------------------------------------------
# Application Advertising decode
# ---------------------------------------------------------------------------

def decode_application(app_bytes: bytes, app_num: int, media_type: int) -> Optional[Dict[str, Any]]:
    """Decode a 4-byte application advertising entry."""
    if len(app_bytes) < 4:
        return None
    host_id = app_bytes[0]
    media_id = app_bytes[1]
    lane_counts = app_bytes[2]
    host_assign = app_bytes[3]

    if host_id == 0 and media_id == 0:
        return None

    host_lane_count = (lane_counts >> 4) & 0x0F
    media_lane_count = lane_counts & 0x0F

    host_name = HOST_INTERFACE_ID.get(host_id, f"Unknown (0x{host_id:02X})")

    if media_type == 0x03:
        media_name = COPPER_MEDIA_INTERFACE_ID.get(media_id, f"Unknown (0x{media_id:02X})")
    else:
        media_name = f"0x{media_id:02X}"

    return {
        "app_num": app_num,
        "host_interface": host_name,
        "host_interface_id": f"0x{host_id:02X}",
        "media_interface": media_name,
        "media_interface_id": f"0x{media_id:02X}",
        "host_lane_count": host_lane_count,
        "media_lane_count": media_lane_count,
        "host_lane_assignment_options": f"0x{host_assign:02X}",
    }


def decode_app_advertising(data: bytes, media_type: int) -> List[Dict[str, Any]]:
    """Decode application advertising from lower page bytes 86-125 (max 10 apps)."""
    apps = []
    for i in range(10):
        offset = i * 4
        if offset + 4 > len(data):
            break
        app = decode_application(data[offset:offset + 4], i + 1, media_type)
        if app is None:
            break
        apps.append(app)
    return apps


# ---------------------------------------------------------------------------
# Lower page decode (bytes 0-127)
# ---------------------------------------------------------------------------

def decode_lower_page(data: bytes) -> Dict[str, Any]:
    """Decode CMIS lower page (bytes 0-127)."""
    if len(data) < 128:
        raise ValueError("Lower page must be 128 bytes")

    ident = data[0]
    rev = data[1]
    status = data[2]
    flags = data[3]

    rev_major = (rev >> 4) & 0x0F
    rev_minor = rev & 0x0F

    flat_memory = bool(status & 0x80)
    intl = bool(status & 0x40)
    module_state_code = (status >> 1) & 0x07
    module_state = MODULE_STATE.get(module_state_code, f"Unknown ({module_state_code})")

    temp_raw = _u16(data[14:16], signed=True)
    temperature = temp_raw / 256.0

    voltage_raw = _u16(data[16:18])
    voltage = voltage_raw * 100e-6  # 100µV units → V

    media_type = data[85] if len(data) > 85 else 0

    app_data = data[86:126] if len(data) >= 126 else b""
    apps = decode_app_advertising(app_data, media_type)

    return {
        "identifier": CMIS_IDENTIFIERS.get(ident, f"Unknown (0x{ident:02X})"),
        "identifier_raw": ident,
        "cmis_revision": f"{rev_major}.{rev_minor}",
        "cmis_revision_raw": f"0x{rev:02X}",
        "flat_memory": flat_memory,
        "intl_deasserted": intl,
        "module_state": module_state,
        "module_state_raw": module_state_code,
        "module_flags_raw": f"0x{flags:02X}",
        "temperature_c": round(temperature, 2),
        "voltage_v": round(voltage, 4),
        "active_firmware": f"{data[39]}.{data[40]}" if len(data) > 40 and (data[39] or data[40]) else "N/A",
        "inactive_firmware": f"{data[41]}.{data[42]}" if len(data) > 42 and (data[41] or data[42]) else "N/A",
        "media_type": MEDIA_TYPE.get(media_type, f"Unknown (0x{media_type:02X})"),
        "media_type_raw": media_type,
        "application_advertising": apps,
    }


# ---------------------------------------------------------------------------
# Upper page 00h decode (bytes 128-255)
# ---------------------------------------------------------------------------

def decode_upper_page_00(data: bytes) -> Dict[str, Any]:
    """Decode CMIS upper page 00h (module identification)."""
    if len(data) < 128:
        raise ValueError("Upper page 00h must be 128 bytes")

    ident = data[0]
    vendor_name = _ascii(data[1:17])
    vendor_oui = data[17:20]
    vendor_pn = _ascii(data[20:36])
    vendor_rev = _ascii(data[36:38])
    vendor_sn = _ascii(data[38:54])
    date_code_raw = data[54:62]
    date_code = _ascii(date_code_raw)
    date_formatted = _format_date(date_code_raw)

    cc_base = data[63]

    # Bytes 72 (offset from page start = 200-128=72): Power characteristics
    power_char = data[72] if len(data) > 72 else 0
    max_power_raw = data[73] if len(data) > 73 else 0
    cable_length_raw = data[74] if len(data) > 74 else 0
    connector_raw = data[75] if len(data) > 75 else 0

    pwr_class, pwr_class_str = decode_power_class(power_char)
    max_power_w = decode_max_power(max_power_raw)
    cable_length_m = decode_cable_length(cable_length_raw)
    connector = CONNECTOR_TYPE.get(connector_raw, f"Unknown (0x{connector_raw:02X})")

    # Media Interface Technology at byte 211 → offset 83
    media_tech_raw = data[83] if len(data) > 83 else 0
    media_tech = MEDIA_INTERFACE_TECH.get(media_tech_raw, f"Unknown (0x{media_tech_raw:02X})")

    # Hardware revision - location varies by CMIS version; omit if uncertain
    # In CMIS, vendor_rev at bytes 36-37 IS the hardware revision.
    # VDM (Versatile Diagnostics Monitoring) support indicator at byte 222 (offset 94 area)
    # Some modules encode it at byte 195 (offset 67)
    vdm_supported = bool(data[67] & 0x40) if len(data) > 67 else False

    # CC_EXT checksum at byte 222 → offset 94
    cc_ext = data[94] if len(data) > 94 else 0

    return {
        "identifier": CMIS_IDENTIFIERS.get(ident, f"0x{ident:02X}"),
        "vendor_name": vendor_name,
        "vendor_oui": "-".join(f"{b:02x}" for b in vendor_oui),
        "vendor_pn": vendor_pn,
        "vendor_rev": vendor_rev,
        "hardware_revision": vendor_rev,
        "vendor_sn": vendor_sn,
        "date_code": date_code,
        "date_code_formatted": date_formatted,
        "cc_base": f"0x{cc_base:02X}",
        "power_class": pwr_class,
        "power_class_description": f"Power Class {pwr_class} ({pwr_class_str} max)" if pwr_class <= 7 else f"Power Class {pwr_class}",
        "max_power_w": max_power_w,
        "cable_assembly_length_m": cable_length_m,
        "connector_type": connector,
        "connector_type_raw": f"0x{connector_raw:02X}",
        "media_interface_technology": media_tech,
        "media_interface_technology_raw": f"0x{media_tech_raw:02X}",
        "vdm_supported": vdm_supported,
        "cc_ext": f"0x{cc_ext:02X}",
    }


# ---------------------------------------------------------------------------
# Full decode entry point
# ---------------------------------------------------------------------------

def decode_all(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Full CMIS EEPROM decode."""
    lower = raw["lower"]
    upper = raw["upper"]

    result: Dict[str, Any] = {
        "standard": "CMIS",
        "coverage": {
            "bytes_read": 128 + 128 * len(upper),
            "pages": sorted(upper.keys()),
            "note": "Lower page (0-127) + upper pages (128-255). Flat memory = single bank.",
        },
        "lower_page": decode_lower_page(lower),
    }

    if 0 in upper:
        result["upper_page_00h"] = decode_upper_page_00(upper[0])

    return result
