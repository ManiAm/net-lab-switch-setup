"""SFF-8472 SFP comprehensive A0h decoder."""

from __future__ import annotations

import struct
from typing import Any, Dict, Optional

from . import codes


def _ascii(buf: bytes) -> str:
    return buf.decode("ascii", errors="replace").strip()


def _u16(buf: bytes, signed: bool = False) -> int:
    if signed:
        return struct.unpack(">h", buf)[0]
    return struct.unpack(">H", buf)[0]


def decode_a0(data: bytes) -> Dict[str, Any]:
    if len(data) < 96:
        raise ValueError("SFP A0h map needs at least 96 bytes")

    diag = data[92] if len(data) > 92 else 0
    opts = data[93] if len(data) > 93 else 0
    br_max = data[66] if len(data) > 66 else 0
    br_min = data[67] if len(data) > 67 else 0

    return {
        "standard": "SFF-8472 (SFP A0h)",
        "identifier": codes.IDENTIFIER.get(data[0], f"0x{data[0]:02X}"),
        "extended_identifier": f"0x{data[1]:02X}",
        "connector": codes.CONNECTOR.get(data[2], f"0x{data[2]:02X}"),
        "specification_compliance": {
            "ethernet": codes.decode_bitmask_str(data[3], codes.ETH_10G_40G),
            "sonet": codes.decode_bitmask_str(data[4], codes.SONET),
            "sas_sata": codes.decode_bitmask_str(data[5], codes.SAS_SATA),
            "gigabit_ethernet": codes.decode_bitmask_str(data[6], codes.GBE),
        },
        "encoding": codes.ENCODING.get(data[11], f"0x{data[11]:02X}"),
        "nominal_bit_rate_100mbd": data[12],
        "rate_identifier": data[13],
        "length_km": data[14],
        "length_100m_om3": data[15],
        "vendor_name": _ascii(data[20:36]),
        "vendor_oui": ":".join(f"{b:02X}" for b in data[37:40]),
        "vendor_pn": _ascii(data[40:56]),
        "vendor_rev": _ascii(data[56:60]),
        "wavelength_nm": _u16(data[60:62]),
        "wavelength_tolerance_nm": _u16(data[62:64]) / 200.0,
        "max_case_temp_c": data[64],
        "cc_base": f"0x{data[63]:02X}",
        "options": {
            "linear_receiver_output": bool(opts & 0x80),
            "power_level_3_required": bool(opts & 0x40),
            "paging_implemented": bool(opts & 0x40),
            "internal_retimer": bool(opts & 0x20),
            "cooled_transmitter": bool(opts & 0x10),
            "power_level_2": bool(opts & 0x08),
            "power_level_1": bool(opts & 0x04),
            "linear_receiver": bool(opts & 0x02),
            "loss_of_signal": bool(opts & 0x01),
            "raw": f"0x{opts:02X}",
        },
        "br_margin_max": br_max,
        "br_margin_min": br_min,
        "vendor_sn": _ascii(data[68:84]),
        "date_code": _ascii(data[84:92]),
        "diagnostic_monitoring": {
            "implemented": bool(diag & 0x40),
            "internally_calibrated": bool(diag & 0x20),
            "externally_calibrated": bool(diag & 0x10),
            "rx_power_measurement_oma": bool(diag & 0x08),
            "address_change_required": bool(diag & 0x04),
            "raw": f"0x{diag:02X}",
        },
        "note": "Live DOM and thresholds are on I2C address A2h (not read by this tool).",
        "vendor_specific_96_127_hex": data[96:128].hex() if len(data) > 127 else None,
    }
