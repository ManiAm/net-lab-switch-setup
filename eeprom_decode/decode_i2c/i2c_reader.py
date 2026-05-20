"""Low-level EEPROM access via Linux sysfs (optoe) or i2c-dev."""

from __future__ import annotations

import os
from typing import List, Optional


class EepromReadError(Exception):
    pass


class EepromReader:
    """Read/write paged EEPROM at I2C address 0x50 (SFF-8636 A0h)."""

    PAGE_SIZE = 256
    DEFAULT_ADDR = 0x50

    def __init__(self, path: Optional[str] = None, bus: Optional[int] = None, addr: int = DEFAULT_ADDR):
        self.path = path
        self.bus = bus
        self.addr = addr
        if path:
            self.path = path
        elif bus is not None:
            self.path = f"/sys/bus/i2c/devices/i2c-{bus}/{bus}-0050/eeprom"
        else:
            raise EepromReadError("Need eeprom path or i2c bus number")

        if not os.path.exists(self.path):
            raise EepromReadError(f"EEPROM path does not exist: {self.path}")

    def _open(self, write: bool = False):
        mode = "r+b" if write else "rb"
        try:
            return open(self.path, mode, buffering=0)
        except PermissionError as e:
            raise EepromReadError(
                f"Permission denied opening {self.path}. "
                "Try sudo or stop xcvrd (docker exec pmon supervisorctl stop xcvrd)."
            ) from e
        except OSError as e:
            raise EepromReadError(f"Cannot open {self.path}: {e}") from e

    def read(self, offset: int, length: int) -> bytes:
        with self._open(write=False) as f:
            f.seek(offset)
            data = f.read(length)
        if len(data) != length:
            raise EepromReadError(f"Short read at offset {offset}: got {len(data)} bytes")
        return data

    def write_byte(self, offset: int, value: int) -> None:
        with self._open(write=True) as f:
            f.seek(offset)
            f.write(bytes([value & 0xFF]))

    def read_lower_page(self) -> bytes:
        return self.read(0, 128)

    def read_upper_page(self, page: int) -> bytes:
        """Select page via byte 127, return 128 bytes that map to offsets 128-255."""
        self.write_byte(127, page & 0xFF)
        return self.read(128, 128)

    def read_all_pages(self, pages: Optional[List[int]] = None, reset_page: bool = True) -> dict:
        if pages is None:
            pages = [0, 1, 2, 3]
        lower = self.read_lower_page()
        upper = {}
        for p in pages:
            upper[p] = self.read_upper_page(p)
        if reset_page:
            try:
                self.write_byte(127, 0)
            except EepromReadError:
                pass
        return {"lower": lower, "upper": upper}
