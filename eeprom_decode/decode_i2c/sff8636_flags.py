"""SFF-8636 lower-page interrupt flag and control bit definitions (from SFF-8636 / ethtool qsfp.h)."""

from __future__ import annotations

from typing import Dict, List, Tuple

# (byte_offset, bit, name) — bit 0 = LSB
AW_FLAGS: List[Tuple[int, int, str]] = [
    # Byte 3 — LOS
    (3, 0, "rx1_los"),
    (3, 1, "rx2_los"),
    (3, 2, "rx3_los"),
    (3, 3, "rx4_los"),
    (3, 4, "tx1_los"),
    (3, 5, "tx2_los"),
    (3, 6, "tx3_los"),
    (3, 7, "tx4_los"),
    # Byte 4 — TX fault
    (4, 0, "tx1_fault"),
    (4, 1, "tx2_fault"),
    (4, 2, "tx3_fault"),
    (4, 3, "tx4_fault"),
    # Byte 6 — temperature
    (6, 4, "temp_low_warning"),
    (6, 5, "temp_high_warning"),
    (6, 6, "temp_low_alarm"),
    (6, 7, "temp_high_alarm"),
    # Byte 7 — Vcc
    (7, 4, "vcc_low_warning"),
    (7, 5, "vcc_high_warning"),
    (7, 6, "vcc_low_alarm"),
    (7, 7, "vcc_high_alarm"),
    # Byte 9 — RX power lanes 1-2
    (9, 0, "rx2_power_low_warning"),
    (9, 1, "rx2_power_high_warning"),
    (9, 2, "rx2_power_low_alarm"),
    (9, 3, "rx2_power_high_alarm"),
    (9, 4, "rx1_power_low_warning"),
    (9, 5, "rx1_power_high_warning"),
    (9, 6, "rx1_power_low_alarm"),
    (9, 7, "rx1_power_high_alarm"),
    # Byte 10 — RX power lanes 3-4
    (10, 0, "rx4_power_low_warning"),
    (10, 1, "rx4_power_high_warning"),
    (10, 2, "rx4_power_low_alarm"),
    (10, 3, "rx4_power_high_alarm"),
    (10, 4, "rx3_power_low_warning"),
    (10, 5, "rx3_power_high_warning"),
    (10, 6, "rx3_power_low_alarm"),
    (10, 7, "rx3_power_high_alarm"),
    # Byte 11 — TX bias lanes 1-2
    (11, 0, "tx2_bias_low_warning"),
    (11, 1, "tx2_bias_high_warning"),
    (11, 2, "tx2_bias_low_alarm"),
    (11, 3, "tx2_bias_high_alarm"),
    (11, 4, "tx1_bias_low_warning"),
    (11, 5, "tx1_bias_high_warning"),
    (11, 6, "tx1_bias_low_alarm"),
    (11, 7, "tx1_bias_high_alarm"),
    # Byte 12 — TX bias lanes 3-4
    (12, 0, "tx4_bias_low_warning"),
    (12, 1, "tx4_bias_high_warning"),
    (12, 2, "tx4_bias_low_alarm"),
    (12, 3, "tx4_bias_high_alarm"),
    (12, 4, "tx3_bias_low_warning"),
    (12, 5, "tx3_bias_high_warning"),
    (12, 6, "tx3_bias_low_alarm"),
    (12, 7, "tx3_bias_high_alarm"),
    # Byte 13 — TX power lanes 1-2
    (13, 0, "tx2_power_low_warning"),
    (13, 1, "tx2_power_high_warning"),
    (13, 2, "tx2_power_low_alarm"),
    (13, 3, "tx2_power_high_alarm"),
    (13, 4, "tx1_power_low_warning"),
    (13, 5, "tx1_power_high_warning"),
    (13, 6, "tx1_power_low_alarm"),
    (13, 7, "tx1_power_high_alarm"),
    # Byte 14 — TX power lanes 3-4
    (14, 0, "tx4_power_low_warning"),
    (14, 1, "tx4_power_high_warning"),
    (14, 2, "tx4_power_low_alarm"),
    (14, 3, "tx4_power_high_alarm"),
    (14, 4, "tx3_power_low_warning"),
    (14, 5, "tx3_power_high_warning"),
    (14, 6, "tx3_power_low_alarm"),
    (14, 7, "tx3_power_high_alarm"),
]


def decode_aw_flags(data: bytes) -> Dict[str, bool]:
    """Return all named alarm/warning flags; True = latched/active."""
    out = {name: False for _, _, name in AW_FLAGS}
    for off, bit, name in AW_FLAGS:
        if off < len(data) and (data[off] >> bit) & 1:
            out[name] = True
    active = {k: v for k, v in out.items() if v}
    return {"all": out, "active": active, "active_count": len(active)}


def decode_tx_disable(byte_val: int) -> Dict[str, bool]:
    return {f"tx{n}_disabled": bool(byte_val & (1 << (n - 1))) for n in range(1, 5)}


def decode_rate_select(byte_val: int) -> Dict[str, str]:
    labels = {0: "default", 1: "rate_1", 2: "rate_2", 3: "rate_3"}
    return {f"lane{n}": labels.get((byte_val >> ((n - 1) * 2)) & 3, "?") for n in range(1, 5)}


def decode_power_control(byte_val: int) -> Dict[str, bool]:
    return {
        "power_override": bool(byte_val & 0x01),
        "power_set": bool(byte_val & 0x02),
        "high_power_class_enable": bool(byte_val & 0x04),
    }
