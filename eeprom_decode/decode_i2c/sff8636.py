"""Comprehensive SFF-8636 QSFP memory map decoder."""

from __future__ import annotations

import math
import struct
from typing import Any, Dict, List, Optional

from . import codes
from . import sff8636_flags as flags


def _ascii(buf: bytes) -> str:
    return buf.decode("ascii", errors="replace").strip()


def _u16(buf: bytes, signed: bool = False) -> int:
    if signed:
        return struct.unpack(">h", buf)[0]
    return struct.unpack(">H", buf)[0]


def _uw_to_dbm(uw: float) -> Optional[float]:
    if uw <= 0:
        return None
    return round(10 * math.log10(uw / 1000.0), 3)


def _threshold_dbm(raw: int, scale: int = 10000) -> Optional[float]:
    if raw in (0, 0xFFFF):
        return None
    mw = raw / scale
    return round(10 * math.log10(mw), 3) if mw > 0 else None


def _rel(page_data: bytes, abs_offset: int) -> int:
    """Absolute EEPROM offset -> index within 128-byte upper page slice."""
    return abs_offset - 128


def _decode_ext_id(b: int) -> Dict[str, Any]:
    power = (b >> 6) & 0x03
    pwr_names = ["Power Class 1 (1.5W)", "Power Class 2 (2.0W)", "Power Class 3 (2.5W)", "Power Class 4 (3.5W)"]
    return {
        "power_class": pwr_names[power],
        "clei_in_page_02h": bool(b & 0x10),
        "cdr_in_tx": bool(b & 0x08),
        "cdr_in_rx": bool(b & 0x04),
        "extended_power_class": b & 0x03,
        "raw": f"0x{b:02X}",
    }


def parse_channel_lanes(data: bytes) -> List[Dict[str, Any]]:
    """Lower-page channel monitor bytes 34–57 (four lanes)."""
    if len(data) < 58:
        return []
    lanes: List[Dict[str, Any]] = []
    for i in range(4):
        rx_uw = _u16(data[34 + i * 2 : 36 + i * 2]) * 0.1
        bias_ma = _u16(data[42 + i * 2 : 44 + i * 2]) * 2e-3
        tx_uw = _u16(data[50 + i * 2 : 52 + i * 2]) * 0.1
        lanes.append(
            {
                "lane": i + 1,
                "rx_power_uw": round(rx_uw, 4),
                "rx_power_dbm": _uw_to_dbm(rx_uw),
                "tx_bias_ma": round(bias_ma, 4),
                "tx_power_uw": round(tx_uw, 4),
                "tx_power_dbm": _uw_to_dbm(tx_uw),
            }
        )
    return lanes


def decode_lower_page(data: bytes) -> Dict[str, Any]:
    if len(data) < 128:
        raise ValueError("Lower page must be 128 bytes")

    status = data[2]
    lanes = parse_channel_lanes(data)

    ctrl = {}
    if len(data) > 86:
        ctrl["tx_disable"] = flags.decode_tx_disable(data[86])
    if len(data) > 87:
        ctrl["rx_rate_select"] = flags.decode_rate_select(data[87])
    if len(data) > 88:
        ctrl["tx_rate_select"] = flags.decode_rate_select(data[88])
    if len(data) > 93:
        ctrl["power_control"] = flags.decode_power_control(data[93])

    return {
        "identifier": codes.IDENTIFIER.get(data[0], f"0x{data[0]:02X}"),
        "identifier_raw": data[0],
        "revision_compliance": codes.REV_COMPLIANCE.get(data[1], f"0x{data[1]:02X}"),
        "revision_compliance_raw": data[1],
        "status": {
            "data_not_ready": bool(status & 0x01),
            "intl_asserted": bool(status & 0x02),
            "page_03h_present_or_flat_memory_bit": bool(status & 0x04),
            "memory_model": "flat (no paging)" if status & 0x04 else "paged",
            "raw": f"0x{status:02X}",
        },
        "alarm_warning_flags": flags.decode_aw_flags(data),
        "module_monitor": {
            "temperature_c": round(_u16(data[22:24], signed=True) / 256.0, 4),
            "vcc_v": round(_u16(data[26:28]) * 1e-4, 4),
        },
        "channel_monitor": lanes,
        "controls": ctrl,
        "vendor_specific_bytes_82_85": data[82:86].hex() if len(data) > 85 else None,
        "page_select": data[127],
        "reserved_bytes_28_33_hex": data[28:34].hex(),
        "reserved_bytes_58_81_hex": data[58:82].hex() if len(data) > 81 else None,
    }


def decode_upper_page_00(data: bytes) -> Dict[str, Any]:
    if len(data) < 128:
        raise ValueError("Upper page 00h must be 128 bytes")

    ext_mod = data[36] if len(data) > 36 else 0
    dev_tech = data[19] if len(data) > 19 else 0
    opt1 = data[64] if len(data) > 64 else 0
    opt2 = data[65] if len(data) > 65 else 0
    opt3 = data[66] if len(data) > 66 else 0
    opt4 = data[67] if len(data) > 67 else 0
    diag = data[92] if len(data) > 92 else 0

    return {
        "identifier": codes.IDENTIFIER.get(data[0], f"0x{data[0]:02X}"),
        "extended_identifier": _decode_ext_id(data[1]),
        "connector": codes.CONNECTOR.get(data[2], f"0x{data[2]:02X}"),
        "specification_compliance": {
            "ethernet_10g_40g": codes.decode_bitmask_str(data[3], codes.ETH_10G_40G),
            "sonet": codes.decode_bitmask_str(data[4], codes.SONET),
            "sas_sata": codes.decode_bitmask_str(data[5], codes.SAS_SATA),
            "gigabit_ethernet": codes.decode_bitmask_str(data[6], codes.GBE),
            "fibre_channel_link_length": codes.decode_bitmask_str(data[7], codes.FC_LINK_LENGTH),
            "fibre_channel_transmitter_tech": codes.decode_bitmask_str(data[7], codes.FC_TRANSMITTER),
            "fibre_channel_transmission_media": codes.decode_bitmask_str(data[9], codes.FC_MEDIA),
            "fibre_channel_speed": codes.decode_bitmask_str(data[10], codes.FC_SPEED),
        },
        "encoding": codes.ENCODING.get(data[11], f"0x{data[11]:02X}"),
        "nominal_bit_rate_100mbd": data[12],
        "nominal_bit_rate_note": "255 = see extended compliance" if data[12] == 255 else None,
        "extended_rate_select": codes.EXT_RATESELECT.get(data[13], f"0x{data[13]:02X}"),
        "length": {
            "smf_km": data[14],
            "om3_2m": data[15],
            "om2_1m": data[16],
            "om1_1m": data[17],
            "cable_assembly_or_om4_m": data[18],
        },
        "device_technology": {
            "transmitter_technology": codes.TRANS_TECH.get((dev_tech >> 4) & 0x0F, f"0x{dev_tech >> 4:01X}"),
            "wavelength_control_active": bool(dev_tech & 0x08),
            "cooled_transmitter": bool(dev_tech & 0x04),
            "apd_pin_detector": bool(dev_tech & 0x02),
            "tunable_transmitter": bool(dev_tech & 0x01),
            "raw": f"0x{dev_tech:02X}",
        },
        "vendor_name": _ascii(data[20:36]),
        "extended_module_codes": codes.EXT_MODULE_CODES.get(
            ext_mod, codes.decode_bitmask_str(ext_mod, {k: v for k, v in codes.EXT_MODULE_CODES.items() if k < 16})
        ),
        "extended_module_codes_raw": ext_mod,
        "vendor_oui": ":".join(f"{b:02X}" for b in data[37:40]),
        "vendor_pn": _ascii(data[40:56]),
        "vendor_rev": _ascii(data[56:58]),
        "wavelength_nm": round(_u16(data[58:60]) / 20.0, 2),
        "wavelength_tolerance_nm": round(_u16(data[60:62]) / 200.0, 3),
        "max_case_temp_c": data[62] if data[62] != 0 else "70 (default)",
        "cc_base_checksum": f"0x{data[63]:02X}",
        "options": {
            "extended_spec_compliance": codes.EXT_SPEC_COMPLIANCE.get(opt1, f"0x{opt1:02X}"),
            "option_byte_193_raw": f"0x{opt2:02X}",
            "rx_output_amplitude_control": bool(opt2 & 0x01),
            "option_byte_194_raw": f"0x{opt3:02X}",
            "tx_squelch_disable": bool(opt3 & 0x02),
            "tx_squelch_implemented": bool(opt3 & 0x01),
            "page_01h_present": bool(opt4 & 0x40),
            "page_02h_present": bool(opt4 & 0x80),
            "rate_select_implemented": bool(opt4 & 0x08),
            "raw_option_195": f"0x{opt4:02X}",
        },
        "vendor_sn": _ascii(data[68:84]),
        "date_code": _ascii(data[84:92]),
        "date_code_formatted": _format_date_code(data[84:92]),
        "diagnostic_monitoring_type": {
            "temperature_monitor_implemented": bool(diag & 0x20),
            "voltage_monitor_implemented": bool(diag & 0x10),
            "rx_power_type_oma": bool(diag & 0x08),
            "tx_power_monitor_implemented": bool(diag & 0x04),
            "tx_bias_monitor_implemented": bool(diag & 0x02),
            "rx_power_monitor_implemented": bool(diag & 0x01),
            "raw": f"0x{diag:02X}",
            "note": "EEPROM capability bits; module may still expose temp/Vcc/bias in lower page",
        },
        "enhanced_options_raw": f"0x{data[93]:02X}" if len(data) > 93 else None,
        "checksum_191_223": f"0x{data[95]:02X}" if len(data) > 95 else None,
        "vendor_specific_96_127_hex": data[96:128].hex() if len(data) > 127 else None,
    }


def _format_date_code(raw: bytes) -> Optional[str]:
    s = _ascii(raw)
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    # SFF-8636 common format: YYMMDD (6 digits) + optional lot code
    if len(s) >= 6 and s[:6].isdigit():
        yy, mm, dd = s[0:2], s[2:4], s[4:6]
        return f"20{yy}-{mm}-{dd}"
    return None


def _trim_field(data: bytes) -> Optional[str]:
    if not data:
        return None
    raw = data.split(b"\x00")[0]
    s = "".join(chr(b) for b in raw if 32 <= b < 127).strip()
    return s or None


def decode_upper_page_01(data: bytes) -> Dict[str, Any]:
    empty = all(x in (0x00, 0xFF) for x in data)
    printable = [] if empty else _extract_printable_strings(data, min_len=4)
    return {
        "empty": empty,
        "non_zero_bytes": sum(1 for x in data if x not in (0x00, 0xFF)),
        "printable_strings": printable,
        "note": "Application Select Table (optional; format is SFF-8636 rev-dependent)",
        "raw_hex": data.hex(),
        "application_advertisement": "N/A" if empty else "(see printable_strings / raw hex)",
    }


def decode_upper_page_02(data: bytes) -> Dict[str, Any]:
    empty = all(x in (0x00, 0xFF) for x in data)
    clei = _extract_clei(data)
    part_number = _trim_field(data[64:80]) if len(data) >= 80 else None
    serial_raw = _trim_field(data[96:112]) if len(data) >= 112 else None
    serial_number = None
    if serial_raw:
        digits = "".join(c for c in serial_raw if c.isdigit())
        serial_number = digits or serial_raw
    ascii_strings = _extract_printable_strings(data)
    known = {s.strip() for s in (clei, part_number, serial_number) if s}

    def _is_redundant(s: str) -> bool:
        t = s.strip()
        if t in known:
            return True
        if serial_number and serial_number in t:
            return True
        if clei and (t in clei or clei in t):
            return True
        if part_number and (t in part_number or part_number in t):
            return True
        return False

    other_strings = [s.strip() for s in ascii_strings if not _is_redundant(s)]
    result: Dict[str, Any] = {
        "empty": empty,
        "note": "User EEPROM / CLEI / vendor fields (layout is vendor-specific)",
        "clei_code": clei,
        "part_number": part_number,
        "serial_number": serial_number,
        "raw_hex": data.hex(),
    }
    if other_strings:
        result["other_ascii_strings"] = other_strings
    return result


def _extract_clei(data: bytes) -> Optional[str]:
    """Heuristic: CLEI often starts with CMUI at the beginning of page 02h."""
    text = data.decode("ascii", errors="ignore")
    for marker in ("CMUI", "CLEI"):
        i = text.find(marker)
        if i >= 0:
            clei = _trim_field(data[i : i + 40])
            if clei:
                return clei
    for start in (0, 2, 4):
        clei = _trim_field(data[start : start + 40])
        if clei and len(clei) >= 10 and clei[0].isalnum():
            return clei
    return None


def _extract_printable_strings(data: bytes, min_len: int = 6) -> List[str]:
    out = []
    cur = []
    for b in data:
        if 32 <= b < 127:
            cur.append(chr(b))
        else:
            if len(cur) >= min_len:
                out.append("".join(cur))
            cur = []
    if len(cur) >= min_len:
        out.append("".join(cur))
    return out


def decode_upper_page_03(data: bytes) -> Dict[str, Any]:
    def temp(abs_off: int) -> float:
        return round(_u16(data[_rel(data, abs_off) : _rel(data, abs_off) + 2], signed=True) / 256.0, 4)

    def volts(abs_off: int) -> float:
        r = _rel(data, abs_off)
        return round(_u16(data[r : r + 2]) / 10000.0, 4)

    def bias_ma(abs_off: int) -> float:
        r = _rel(data, abs_off)
        return round(_u16(data[r : r + 2]) / 500.0, 4)

    def dbm_at(abs_off: int) -> Optional[float]:
        r = _rel(data, abs_off)
        return _threshold_dbm(_u16(data[r : r + 2]))

    module = {
        "temp_high_alarm_c": temp(128),
        "temp_low_alarm_c": temp(130),
        "temp_high_warning_c": temp(132),
        "temp_low_warning_c": temp(134),
        "vcc_high_alarm_v": volts(144),
        "vcc_low_alarm_v": volts(146),
        "vcc_high_warning_v": volts(148),
        "vcc_low_warning_v": volts(150),
        "rx_power_high_alarm_dbm": dbm_at(176),
        "rx_power_low_alarm_dbm": dbm_at(178),
        "rx_power_high_warning_dbm": dbm_at(180),
        "rx_power_low_warning_dbm": dbm_at(182),
        "tx_bias_high_alarm_ma": bias_ma(184),
        "tx_bias_low_alarm_ma": bias_ma(186),
        "tx_bias_high_warning_ma": bias_ma(188),
        "tx_bias_low_warning_ma": bias_ma(190),
        "tx_power_high_alarm_dbm": dbm_at(192),
        "tx_power_low_alarm_dbm": dbm_at(194),
        "tx_power_high_warning_dbm": dbm_at(196),
        "tx_power_low_warning_dbm": dbm_at(198),
    }

    # Bytes 136-175 reserved in spec between temp and Vcc groups — include hex
    reserved_136_143 = data[_rel(data, 136) : _rel(data, 144)].hex()
    reserved_152_175 = data[_rel(data, 152) : _rel(data, 176)].hex()

    return {
        "module_thresholds": module,
        "reserved_136_143_hex": reserved_136_143,
        "reserved_152_175_hex": reserved_152_175,
        "vendor_specific_200_255_hex": data[_rel(data, 200) :].hex() if len(data) > _rel(data, 200) else None,
    }


def summarize_page_01(decoded: Dict[str, Any]) -> Dict[str, Any]:
    """Short summary for byte-map text output (page 01h)."""
    if decoded.get("empty"):
        return {
            "status": "Empty — no application select table (all 0x00 / 0xFF)",
            "note": decoded.get("note"),
        }
    return {
        "status": "Application select table present",
        "non_zero_bytes": decoded.get("non_zero_bytes"),
        "printable_strings": decoded.get("printable_strings") or "(none)",
        "note": decoded.get("note"),
    }


def summarize_page_02(decoded: Dict[str, Any]) -> Dict[str, Any]:
    """Short summary for byte-map text output (page 02h)."""
    if decoded.get("empty"):
        return {
            "status": "Empty — user EEPROM not programmed (all 0x00 / 0xFF)",
            "note": decoded.get("note"),
        }
    summary: Dict[str, Any] = {
        "clei_code": decoded.get("clei_code") or "(not found)",
        "part_number": decoded.get("part_number") or "(not found)",
        "serial_number": decoded.get("serial_number") or "(not found)",
        "note": decoded.get("note"),
    }
    if decoded.get("other_ascii_strings"):
        summary["other_ascii_strings"] = decoded["other_ascii_strings"]
    return summary


def decode_all(raw: Dict[str, Any]) -> Dict[str, Any]:
    lower = raw["lower"]
    upper = raw["upper"]
    result: Dict[str, Any] = {
        "standard": "SFF-8636",
        "coverage": {
            "bytes_read": 128 + 128 * len(upper),
            "pages": sorted(upper.keys()),
            "note": "Lower page + upper pages read at I2C address A0h (0x50)",
        },
        "lower_page": decode_lower_page(lower),
    }
    if 0 in upper:
        result["upper_page_00h_identification"] = decode_upper_page_00(upper[0])
    if 1 in upper:
        result["upper_page_01h"] = decode_upper_page_01(upper[1])
    if 2 in upper:
        result["upper_page_02h_user_eeprom"] = decode_upper_page_02(upper[2])
    if 3 in upper:
        result["upper_page_03h_thresholds"] = decode_upper_page_03(upper[3])
    return result
