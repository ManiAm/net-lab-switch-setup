"""Code tables for SFF-8636 / SFF-8472."""

from __future__ import annotations

from typing import Dict, List

IDENTIFIER = {
    0x00: "Unknown",
    0x01: "GBIC",
    0x02: "Module/connector soldered to motherboard",
    0x03: "SFP/SFP+/SFP28",
    0x0B: "DWDM-SFP",
    0x0C: "QSFP",
    0x0D: "QSFP+ or later",
    0x11: "QSFP28 or later",
    0x18: "QSFP-DD",
    0x1E: "OSFP",
}

REV_COMPLIANCE = {
    0: "Unspecified",
    1: "SFF-8436 Rev 4.8 or earlier",
    2: "SFF-8436 Rev 4.8+ with exceptions",
    3: "SFF-8636 Rev 1.3 or earlier",
    4: "SFF-8636 Rev 1.4",
    5: "SFF-8636 Rev 1.5",
    6: "SFF-8636 Rev 2.0",
    7: "SFF-8636 Rev 2.5–2.7",
    8: "SFF-8636 Rev 2.8–2.10",
}

CONNECTOR = {
    0x00: "Unknown",
    0x01: "SC",
    0x07: "LC",
    0x0B: "Optical pigtail",
    0x0C: "MPO 1x12",
    0x0D: "MPO 2x16",
    0x21: "Copper pigtail",
    0x23: "No separable connector",
}

ENCODING = {
    0x00: "Unspecified",
    0x01: "8B/10B",
    0x02: "4B/5B",
    0x03: "NRZ",
    0x04: "SONET Scrambled",
    0x05: "64B/66B",
    0x06: "Manchester",
    0x07: "256B/257B",
    0x08: "PAM4",
}

EXT_SPEC_COMPLIANCE = {
    0x00: "Unspecified",
    0x01: "100G AOC or 25G AOC",
    0x02: "100GBASE-SR4 or 25GBASE-SR",
    0x03: "100GBASE-LR4",
    0x04: "100GBASE-ER4",
    0x05: "100GBASE-SR10",
    0x06: "100G CWDM4",
    0x07: "100G PSM4 Parallel SMF",
    0x08: "100G ACC",
    0x09: "100GBASE-CR4",
    0x0A: "25GBASE-CR CA-S",
    0x0B: "25GBASE-CR CA-L (RS-FEC)",
    0x0C: "25GBASE-CR CA-N (no FEC)",
    0x0D: "25GBASE-CR CA-N or 50GBASE-CR2 with no FEC",
    0x0E: "10GBASE-T with SFI",
    0x0F: "50GBASE-CR",
}

EXT_MODULE_CODES = {
    0: "N/A",
    1: "HDR",
    2: "EDR",
    3: "HDR, EDR",
    4: "FDR",
    6: "EDR, FDR",
    7: "HDR, EDR, FDR",
    8: "QDR",
    12: "FDR, QDR",
    14: "EDR, FDR, QDR",
    15: "HDR, EDR, FDR, QDR",
    16: "DDR",
    24: "QDR, DDR",
    28: "FDR, QDR, DDR",
    30: "EDR, FDR, QDR, DDR",
    31: "HDR, EDR, FDR, QDR, DDR",
}

EXT_RATESELECT = {0: "Unspecified", 1: "Rate Select Version 1", 2: "Rate Select Version 2"}

# Bitmask tables: bit position -> name
ETH_10G_40G = {
    0: "40G Active Cable (XLPPI)",
    1: "40GBASE-LR4",
    2: "40GBASE-SR4",
    3: "40GBASE-CR4",
    4: "10GBASE-SR",
    5: "10GBASE-LR",
    6: "10GBASE-LRM",
    7: "Extended",
}

SONET = {0: "OC 48 SR", 1: "OC 48 IR", 2: "OC 48 LR", 3: "40G OTN"}

SAS_SATA = {4: "SAS 3G", 5: "SAS 6G", 6: "SAS 12G", 7: "SAS 24G"}

GBE = {0: "1000BASE-SX", 1: "1000BASE-LX", 2: "1000BASE-CX", 3: "1000BASE-T"}

FC_LINK_LENGTH = {
    3: "Medium (M)",
    4: "Long (L)",
    5: "Intermediate (I)",
    6: "Short (S)",
    7: "Very long (V)",
}

FC_TRANSMITTER = {
    0: "Electrical inter-enclosure",
    1: "Longwave Laser (LC)",
    4: "Longwave Laser (LL)",
    5: "Shortwave laser w/OFC",
    6: "Shortwave laser w/o OFC",
    7: "Electrical intra-enclosure",
}

FC_MEDIA = {
    0: "Single Mode",
    1: "OM3 50um",
    2: "OM2 50m",
    3: "OM1 62.5m",
    4: "Video coax",
    5: "Mini coax",
    6: "Shielded twisted pair",
    7: "Twin axial",
}

FC_SPEED = {0: "100 MBytes/s", 2: "200 MBytes/s", 4: "400 MBytes/s", 5: "1600 MBytes/s", 6: "800 MBytes/s", 7: "1200 MBytes/s"}

TRANS_TECH = {
    0: "850nm VCSEL",
    1: "1310nm VCSEL",
    2: "1550nm VCSEL",
    3: "1310nm FP",
    4: "1310nm DFB",
    5: "1550nm DFB",
    6: "1310nm EML",
    7: "1550nm EML",
    8: "Others",
    9: "1490nm DFB",
    10: "Copper unequalized",
    11: "Copper passive equalized",
    12: "Copper near+far equalized",
    13: "Copper far equalized",
    14: "Copper near equalized",
    15: "Copper linear active equalizers",
}


def decode_bitmask(value: int, table: Dict[int, str]) -> List[str]:
    if value == 0:
        return ["None"]
    names = [table[b] for b in sorted(table) if value & (1 << b)]
    return names or [f"0x{value:02X}"]


def decode_bitmask_str(value: int, table: Dict[int, str]) -> str:
    names = decode_bitmask(value, table)
    return ", ".join(names) if names != ["None"] else "None"
