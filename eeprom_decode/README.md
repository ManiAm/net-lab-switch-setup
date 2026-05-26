# xcvr_decode

Read and decode transceiver EEPROM — supports **CMIS** (QSFP-DD / OSFP), **SFF-8636** (QSFP/QSFP28), and **SFF-8472** (SFP).

## Requirements

- Python 3.8+
- One of:
  - Linux sysfs EEPROM access (`optoe` / `at24` at **0x50**)
  - SONiC platform SDK (Nvidia/Mellanox SN-series, others)
- **Read** for lower page; **write** for upper-page select (byte 127) — use `sudo` if needed

## Usage

```bash
# SONiC port (auto-detects platform and selects I2C or SDK backend)
python3 xcvr_decode.py Ethernet0

# Direct path or bus number (any Linux host)
python3 xcvr_decode.py --eeprom-path /sys/bus/i2c/devices/i2c-30/30-0050/eeprom
python3 xcvr_decode.py --i2c-bus 30

# JSON (structured decode) or raw hex only
python3 xcvr_decode.py Ethernet0 --json
python3 xcvr_decode.py Ethernet0 --raw
```

Skip optional upper pages:

```bash
python3 xcvr_decode.py Ethernet16 --no-page1 --no-page2
```

Also works as a Python module:

```bash
python3 -m xcvr_decode Ethernet0
```

## How it works

1. **Detect platform** — reads `/etc/sonic/device_metadata.json` or `sonic-cfggen`
2. **Resolve access** — looks up `xcvr_decode.yaml` for backend type (I2C sysfs vs SDK)
3. **Read EEPROM** — lower page (0–127) + upper pages (128–255, page-select via byte 127)
4. **Auto-detect standard** — identifier byte 0 determines CMIS vs SFF-8636 vs SFF-8472
5. **Decode & format** — human-readable byte-map output with live telemetry

## Platform configuration

Edit `xcvr_decode.yaml` (next to the script, or `/etc/xcvr_decode.yaml`):

```yaml
platforms:
  x86_64-cel_seastone-r0:
    i2c_start: 26
    port_index: "eth//4"
    eeprom_template: "/sys/bus/i2c/devices/i2c-{bus}/{bus}-0050/eeprom"

  x86_64-nvidia_sn5600-r0:
    backend: sdk
    port_index: "eth//8"
    sfp_index_offset: 1
```

Resolution order:

1. `--eeprom-path` (explicit file path)
2. `--i2c-bus` (builds sysfs path)
3. `XCVR_DECODE_EEPROM_PATH` env var
4. `xcvr_decode.yaml` + auto-detected SONiC platform + `EthernetN`

## What is decoded

| Standard | Identifiers | Output |
|----------|-------------|--------|
| **CMIS 4.x/5.x** | QSFP-DD (0x18), OSFP-8X (0x19), OSFP (0x1E) | Module info, live temp/voltage/per-lane DOM, firmware, app advertising |
| **SFF-8636** | QSFP (0x0C), QSFP+ (0x0D), QSFP28 (0x11) | Byte-map + per-lane DOM table + thresholds (page 03h) |
| **SFF-8472** | SFP (0x03) | A0h identification fields |
| Unknown | Any other | Hex dump + note |

## Code layout

```
xcvr_decode.py             # entry point
xcvr_decode.yaml           # platform → backend configuration
xcvr_decode/
  __init__.py              # package version
  __main__.py              # python -m xcvr_decode
  cli.py                   # argument parsing, read orchestration, dispatch
  backends.py              # platform detection, path/SDK resolution
  eeprom_reader.py         # low-level I/O (sysfs EepromReader + SdkEepromReader)
  cmis.py                  # CMIS structured decoder (lower page + page 00h)
  cmis_bytemap.py          # CMIS byte-map text formatter
  sff8636.py               # SFF-8636 structured decoder (all pages)
  sff8636_bytemap.py       # SFF-8636 byte-map field definitions
  sff8636_format.py        # SFF-8636 text formatter
  sff8636_flags.py         # SFF-8636 alarm/control bit definitions
  sff8472.py               # SFF-8472 SFP A0h decoder
  codes.py                 # shared SFF code tables (identifiers, connectors, etc.)
  format_output.py         # shared text formatting (banners, tables, JSON)
```

## Design principles

- **Independent** — does not rely on SONiC `xcvrd`, `sfpshow`, or vendor decoder libraries
- **Standard-driven** — follows CMIS 5.2, SFF-8636, SFF-8472, and SFF-8024 specifications
- **Modular** — each standard has its own decoder + formatter; shared code is minimal
- **Graceful degradation** — passive copper DACs (flat memory) are handled without errors
