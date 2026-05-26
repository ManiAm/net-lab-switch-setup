"""Low-level EEPROM access via Linux sysfs (optoe), i2c-dev, or SONiC platform SDK."""

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


class SdkEepromReader:
    """Read EEPROM via SONiC platform API (Mellanox SDK).

    Used on platforms (e.g. Nvidia SN5600) where transceivers are not
    exposed as sysfs I2C EEPROM files but accessed through the SDK.
    """

    PAGE_SIZE = 256

    def __init__(self, platform_sfp_index: int):
        self.platform_sfp_index = platform_sfp_index
        self._sfp = None
        self._flat_memory = None

    def _get_sfp(self):
        if self._sfp is None:
            try:
                from sonic_platform.chassis import Chassis
            except ImportError as e:
                raise EepromReadError(
                    "sonic_platform module not available. "
                    "Run on SONiC host or use --eeprom-path / --i2c-bus."
                ) from e
            chassis = Chassis()
            self._sfp = chassis.get_sfp(self.platform_sfp_index)
            if self._sfp is None:
                raise EepromReadError(
                    f"SFP at platform index {self.platform_sfp_index} does not exist "
                    f"(index out of range for this platform)"
                )
            if not self._sfp.get_presence():
                raise EepromReadError(
                    f"SFP at platform index {self.platform_sfp_index} is not present"
                )
        return self._sfp

    def _is_flat_memory(self) -> bool:
        """Detect flat memory from EEPROM status bits.

        Also treats the module as flat if write_eeprom is unsupported
        (common on Nvidia SDK platforms where writes always fail).
        """
        if self._flat_memory is None:
            sfp = self._get_sfp()
            lower = sfp.read_eeprom(0, 3)
            if lower is None or len(lower) < 3:
                self._flat_memory = True
                return True
            ident = lower[0]
            if ident in (0x18, 0x19, 0x1E):
                self._flat_memory = bool(lower[2] & 0x80)
            elif ident in (0x0C, 0x0D, 0x11):
                self._flat_memory = bool(lower[2] & 0x04)
            else:
                self._flat_memory = True
            if not self._flat_memory:
                test = sfp.write_eeprom(127, 1, bytearray([0x00]))
                if test is False:
                    self._flat_memory = True
        return self._flat_memory

    def read(self, offset: int, length: int) -> bytes:
        sfp = self._get_sfp()
        data = sfp.read_eeprom(offset, length)
        if data is None:
            raise EepromReadError(
                f"SDK read_eeprom returned None at offset {offset} length {length}"
            )
        if len(data) != length:
            raise EepromReadError(f"Short read at offset {offset}: got {len(data)} bytes")
        return data

    def write_byte(self, offset: int, value: int) -> None:
        sfp = self._get_sfp()
        result = sfp.write_eeprom(offset, 1, bytearray([value & 0xFF]))
        if result is False:
            raise EepromReadError(f"SDK write_eeprom failed at offset {offset}")

    def read_lower_page(self) -> bytes:
        return self.read(0, 128)

    def read_upper_page(self, page: int) -> bytes:
        """Select page via byte 127, return 128 bytes at offsets 128-255."""
        if self._is_flat_memory():
            if page == 0:
                return self.read(128, 128)
            return bytes(128)
        self.write_byte(127, page & 0xFF)
        return self.read(128, 128)

    def read_all_pages(self, pages: Optional[List[int]] = None, reset_page: bool = True) -> dict:
        if pages is None:
            pages = [0, 1, 2, 3]
        lower = self.read_lower_page()
        upper = {}
        if self._is_flat_memory():
            upper_data = self.read(128, 128)
            for p in pages:
                upper[p] = upper_data if p == 0 else bytes(128)
        else:
            for p in pages:
                upper[p] = self.read_upper_page(p)
            if reset_page:
                try:
                    self.write_byte(127, 0)
                except EepromReadError:
                    pass
        return {"lower": lower, "upper": upper}
