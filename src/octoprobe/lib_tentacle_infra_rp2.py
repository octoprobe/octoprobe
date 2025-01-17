from __future__ import annotations

from .lib_tentacle import TentacleInfra


class InfraRP2:
    """
    This class wrapps all the calls to
    micropython running on
    the infrastructure-RP2 on the tentacle.

    The interface is type save and all micropython code is hidden in this class.
    """

    BASE_CODE = """
import os
import sys
import time
from machine import Pin, unique_id
import ubinascii

rp2_unique_id = ubinascii.hexlify(unique_id()).decode('ascii')
files_on_flash = len(os.listdir())

pin_led_active = Pin('GPIO24', Pin.OUT)

pin_relays = {
    1: Pin('GPIO1', Pin.OUT),
    2: Pin('GPIO2', Pin.OUT),
    3: Pin('GPIO3', Pin.OUT),
    4: Pin('GPIO4', Pin.OUT),
    5: Pin('GPIO5', Pin.OUT),
    6: Pin('GPIO6', Pin.OUT),
    7: Pin('GPIO7', Pin.OUT),
}

def set_relays(list_relays):
    for i, close  in list_relays:
        pin_relays[i].value(close)

def set_relays_pulse(relays, initial_closed, durations_ms):
    pin = pin_relays[relays]
    pin.value(initial_closed)
    for duration_ms in durations_ms:
       time.sleep_ms(duration_ms)
       pin.toggle()
"""

    def __init__(self, tentacle_infra: TentacleInfra) -> None:
        assert tentacle_infra.__class__.__qualname__ == "TentacleInfra"
        self._infra = tentacle_infra
        self._base_code_loaded = False

    def _load_base_code(self) -> None:
        if self._base_code_loaded:
            return
        assert self._infra.mp_remote is not None
        self._infra.mp_remote.exec_raw(self.BASE_CODE)

    def get_unique_id(self) -> str:
        self._load_base_code()
        return self._infra.mp_remote.read_str("rp2_unique_id")

    def get_micropython_version(self) -> str:
        self._load_base_code()
        return self._infra.mp_remote.read_str(
            "sys.version + ',' + sys.implementation[2]"
        )

    def exception_if_files_on_flash(self) -> None:
        # "import os; print('main.py' in os.listdir())"
        self._load_base_code()
        file_count = self._infra.mp_remote.read_int("files_on_flash")
        if file_count == 0:
            return

        raise ValueError(
            f"{self._infra.label}: Found {file_count} files on flash!': Please remove them!"
        )

    def relays(
        self,
        relays_close: list[int] | None = None,
        relays_open: list[int] | None = None,
    ) -> None:
        """
        If the same relays appears in 'relays_open' and 'relays_close': The relay will be CLOSED.
        """
        if relays_close is None:
            relays_close = []
        if relays_open is None:
            relays_open = []

        assert isinstance(relays_close, list)
        assert isinstance(relays_open, list)

        self._load_base_code()

        for i in relays_close + relays_open:
            assert self._infra.is_valid_relay_index(i)

        dict_relays = {}
        for i in relays_open:
            dict_relays[i] = False
        for i in relays_close:
            dict_relays[i] = True
        list_relays = list(dict_relays.items())

        self._infra.mp_remote.exec_raw(cmd=f"set_relays({list_relays})")

    def relays_pulse(
        self,
        relays: int,
        initial_closed: bool,
        durations_ms: list[int],
    ) -> None:
        """
        Makes relays number 'relays' sending pulses. 'relays' corresponds to the number printed on the PCB.
        If 'initial_closed' is True: The relays will initially closed..
        For all 'durations_ms': Sleep for 'duration_ms', then toggle the relays.
        """
        assert 1 <= relays < 7  # lib_tentacle_infra.py TentacleInfra.RELAY_COUNT
        assert isinstance(initial_closed, bool)
        assert isinstance(durations_ms, list)
        for duration_ms in durations_ms:
            assert isinstance(duration_ms, int)

        self._load_base_code()

        self._infra.mp_remote.exec_raw(
            cmd=f"set_relays_pulse(relays={relays}, initial_closed={initial_closed}, durations_ms={durations_ms})",
            timeout=int(1.5 * 1000 * sum(durations_ms)),
        )

    def active_led(self, on: bool) -> None:
        assert isinstance(on, bool)
        self._load_base_code()

        self._infra.mp_remote.exec_raw(cmd=f"pin_led_active.value({int(on)})")
