# decode_i2c

Read and decode transceiver EEPROM over I²C (SFF-8636 QSFP/QSFP28, SFF-8472 SFP).

## Requirements

- Linux with module EEPROM on sysfs (`…/eeprom`, typically `optoe` / `at24` at **0x50**)
- **Read** for lower page; **write** for upper-page select (byte 127) — use `sudo` on SONiC if needed
- Python 3.8+

## Usage

```bash
# SONiC port (needs platform block in decode_i2c.yaml)
sudo ./decode_i2c.py Ethernet16

# Any host — direct path or bus number
sudo ./decode_i2c.py --eeprom-path /sys/bus/i2c/devices/i2c-30/30-0050/eeprom
sudo ./decode_i2c.py --i2c-bus 30

# JSON (structured decode) or raw hex only
sudo ./decode_i2c.py Ethernet16 --json
./decode_i2c.py Ethernet16 --raw
```

Skip optional upper pages:

```bash
sudo ./decode_i2c.py Ethernet16 --no-page1 --no-page2
```

## Output (QSFP / SFF-8636)

Text mode prints EEPROM **in byte address order** with section headings:

- Lower page: identity, status, alarms, live DOM, controls, page select
- Upper **00h**: identification and compliance (vendor, wavelength, options)
- Upper **01h** / **02h**: hex lines plus a short decoded summary
- Upper **03h**: alarm/warning thresholds
- Per-lane DOM table after channel monitor bytes

Unmapped bytes: `** Reserved **` plus hex.

## How the port maps to I²C (SONiC)

Resolution order:

1. `--eeprom-path`
2. `--i2c-bus` (builds `i2c-{bus}/{bus}-0050/eeprom`)
3. `DECODE_I2C_EEPROM_PATH`
4. `decode_i2c.yaml` + SONiC platform string + `EthernetN`

Platform detection reads `/etc/sonic/device_metadata.json` or `sonic-cfggen`.  
Add another switch by editing `decode_i2c.yaml` (no code change for linear bus numbering).

Example (Celestica DX010 / Seastone):

| Field | Value |
|--------|--------|
| `i2c_start` | 26 |
| `port_index` | `eth//4` → Ethernet16 → index 4 → bus **30** |

## What is decoded

| Standard | Text output | `--json` |
|----------|-------------|----------|
| **SFF-8636** (QSFP+) | Byte-map + summaries | Full nested decode |
| **SFF-8472** (SFP) | A0h fields only | A0h fields only |
| Other ID | Note + hex keys | Raw hex |

SFP live DOM and thresholds are on **A2h** — not read by this tool.

## Layout (code)

```
decode_i2c.py          # launcher
decode_i2c.yaml        # platform → I²C bus mapping
decode_i2c/
  cli.py               # arguments, read, dispatch
  backends.py          # path resolution
  i2c_reader.py        # sysfs paging read
  sff8636.py           # structured decode (JSON)
  sff8636_bytemap.py   # byte-address field map (text)
  sff8636_flags.py     # alarm / control bit names
  bytemap_format.py    # QSFP text formatter
  format_output.py     # banners, tables, SFP text
  codes.py             # SFF code tables
  sff8472.py           # SFP A0h
```

Decoding follows **SFF-8636 / SFF-8472**, not SONiC `xcvrd` or `sfpshow`.
