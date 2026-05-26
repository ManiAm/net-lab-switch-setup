"""Hardware / OS backends: resolve interface name -> EEPROM path or SDK reader."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .eeprom_reader import EepromReader, EepromReadError, SdkEepromReader


@dataclass
class ResolvedPath:
    interface: str
    eeprom_path: str
    backend: str
    meta: dict


def _package_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_yaml_platforms() -> dict:
    """Minimal YAML subset without PyYAML dependency."""
    paths = [
        _package_dir() / "xcvr_decode.yaml",
        Path("/etc/xcvr_decode.yaml"),
    ]
    platforms = {}
    for p in paths:
        if not p.is_file():
            continue
        current = None
        for line in p.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if line == "platforms:":
                continue
            if line.endswith(":") and not line.startswith(" "):
                current = line[:-1].strip()
                platforms[current] = {}
                continue
            if current and ":" in line:
                k, v = line.split(":", 1)
                platforms[current][k.strip()] = v.strip().strip('"').strip("'")
    return platforms


def _sonic_platform() -> Optional[str]:
    try:
        import json

        with open("/etc/sonic/device_metadata.json") as f:
            meta = json.load(f)
        return meta.get("DEVICE_METADATA", {}).get("localhost", {}).get("platform")
    except (OSError, json.JSONDecodeError, ImportError):
        pass
    try:
        result = subprocess.run(
            ["sonic-cfggen", "-d", "-v", "DEVICE_METADATA.localhost.platform"],
            capture_output=True, text=True, timeout=5,
        )
        out = result.stdout.strip()
        return out or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _eth_index(name: str) -> int:
    m = re.match(r"^Ethernet(\d+)$", name, re.I)
    if not m:
        raise EepromReadError(f"Not a SONiC Ethernet interface name: {name}")
    return int(m.group(1))


def _eval_port_index(expr: str, eth: int) -> int:
    expr = expr.strip().lower()
    if expr in ("eth//8", "eth/8"):
        return eth // 8
    if expr in ("eth//4", "eth/4"):
        return eth // 4
    if expr == "eth":
        return eth
    raise EepromReadError(f"Unsupported port_index in config: {expr!r} (use eth//8, eth//4, or eth)")


def resolve_eeprom_path(
    interface: Optional[str] = None,
    eeprom_path: Optional[str] = None,
    i2c_bus: Optional[int] = None,
    i2c_addr: int = 0x50,
) -> ResolvedPath:
    if eeprom_path:
        return ResolvedPath(
            interface=interface or "direct",
            eeprom_path=eeprom_path,
            backend="direct",
            meta={"i2c_addr": hex(i2c_addr)},
        )

    if i2c_bus is not None:
        path = f"/sys/bus/i2c/devices/i2c-{i2c_bus}/{i2c_bus}-0050/eeprom"
        return ResolvedPath(
            interface=interface or f"i2c-{i2c_bus}",
            eeprom_path=path,
            backend="i2c_bus",
            meta={"bus": i2c_bus, "addr": hex(i2c_addr)},
        )

    env = os.environ.get("XCVR_DECODE_EEPROM_PATH") or os.environ.get("DECODE_I2C_EEPROM_PATH")
    if env:
        return ResolvedPath(
            interface=interface or "env",
            eeprom_path=env,
            backend="env",
            meta={},
        )

    if not interface:
        raise EepromReadError("Specify interface, --eeprom-path, or --i2c-bus")

    platforms = _load_yaml_platforms()
    platform = _sonic_platform()
    if not platform:
        raise EepromReadError(
            "Cannot detect SONiC platform. Use --eeprom-path, --i2c-bus, or DECODE_I2C_EEPROM_PATH."
        )
    cfg = platforms.get(platform)
    if not cfg:
        known = ", ".join(sorted(platforms.keys())) or "(none)"
        raise EepromReadError(
            f"No mapping for platform {platform!r} in xcvr_decode.yaml. "
            f"Known platforms: {known}. "
            "Add a platform block or use --eeprom-path / --i2c-bus."
        )

    eth = _eth_index(interface)
    backend_type = cfg.get("backend", "i2c")
    port_index_expr = cfg.get("port_index", "eth//4")
    idx = _eval_port_index(port_index_expr, eth)

    if backend_type == "sdk":
        sfp_index_offset = int(cfg.get("sfp_index_offset", 1))
        platform_sfp_index = idx + sfp_index_offset
        return ResolvedPath(
            interface=interface,
            eeprom_path=f"sdk://platform_sfp_index={platform_sfp_index}",
            backend=f"sdk:{platform}",
            meta={"eth": eth, "port_index": idx, "platform_sfp_index": platform_sfp_index},
        )

    i2c_start = int(cfg.get("i2c_start", 26))
    bus = i2c_start + idx

    template = cfg.get(
        "eeprom_template",
        "/sys/bus/i2c/devices/i2c-{bus}/{bus}-0050/eeprom",
    )
    path = template.format(bus=bus, index=idx, eth=eth)

    return ResolvedPath(
        interface=interface,
        eeprom_path=path,
        backend=f"config:{platform}",
        meta={"eth": eth, "qsfp_index": idx, "i2c_bus": bus},
    )


def open_reader(
    interface: Optional[str] = None,
    eeprom_path: Optional[str] = None,
    i2c_bus: Optional[int] = None,
    i2c_addr: int = 0x50,
) -> tuple[Union[EepromReader, SdkEepromReader], ResolvedPath]:
    resolved = resolve_eeprom_path(interface, eeprom_path, i2c_bus, i2c_addr)
    if resolved.backend.startswith("sdk:"):
        reader = SdkEepromReader(platform_sfp_index=resolved.meta["platform_sfp_index"])
    else:
        reader = EepromReader(path=resolved.eeprom_path)
    return reader, resolved
