from __future__ import annotations

import contextlib
import logging
import typing

from .lib_tentacle import TentacleInfra
from .usb_tentacle.usb_constants import HwVersion
from .util_jinja2 import render

logger = logging.getLogger(__name__)


class InfraPico:
    """
    This class wrapps all the calls to
    micropython running on
    the infrastructure-Pico on the tentacle.

    The interface is type save and all micropython code is hidden in this class.
    """

    _MICROPYTHON_BASE_CODE_JINJA2 = """
import os
import sys
import time
from machine import Pin, unique_id
import ubinascii

pico_unique_id = ubinascii.hexlify(unique_id()).decode('ascii')
gpio_hw_version = 0
for _gpio in (29, 28, 27, 26, 25):
    gpio_hw_version = 2 * gpio_hw_version + Pin(_gpio, Pin.IN, Pin.PULL_DOWN).value()
files_on_flash = len(os.listdir())

pin_led_active = Pin('GPIO24', Pin.OUT)
pin_led_error = Pin('GPIO20', Pin.OUT) # Not connected on v0.3
pin_power_dut = Pin('GPIO23', Pin.OUT) # Not connected on v0.3
pin_power_proberun = Pin('GPIO22', Pin.OUT) # Not connected on v0.3
pin_power_probeboot = Pin('GPIO21', Pin.OUT) # Not connected on v0.3

pin_relays = {
{% for gpio in (1, 2, 3, 4, 5, 6, 7) %}
    {{ loop.index }}: Pin('GPIO{{ gpio }}', Pin.OUT),
{%- endfor %}
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
        assert isinstance(tentacle_infra, TentacleInfra)
        self._infra = tentacle_infra
        self._base_code_loaded = False
        self._gpio_hw_version: int | None = None
        self._unique_id: str | None = None

    def load_base_code(self) -> None:
        if self._base_code_loaded:
            return
        assert self._infra.mp_remote is not None
        micropython_base_code = render(
            micropython_code=self._MICROPYTHON_BASE_CODE_JINJA2
        )
        self._infra.mp_remote.exec_raw(micropython_base_code)
        self._unique_id = self._infra.mp_remote.read_str("pico_unique_id")
        self._gpio_hw_version = self._infra.mp_remote.read_int("gpio_hw_version")

    @property
    def gpio_hw_version(self) -> int:
        if self._gpio_hw_version is None:
            self.load_base_code()
            assert self._gpio_hw_version is not None
        return self._gpio_hw_version

    @property
    def hw_version(self) -> str:
        return {0: HwVersion.V03, 1: HwVersion.V05}[self.gpio_hw_version]

    @property
    def unique_id(self) -> str:
        if self._unique_id is None:
            self.load_base_code()
            assert self._unique_id is not None
        return self._unique_id

    def get_micropython_version(self) -> str:
        self.load_base_code()
        return self._infra.mp_remote.read_str(
            "sys.version + ',' + sys.implementation[2]"
        )

    def exception_if_files_on_flash(self) -> None:
        # "import os; print('main.py' in os.listdir())"
        self.load_base_code()
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

        self.load_base_code()

        for i in relays_close + relays_open:
            assert self._infra.is_valid_relay_index(i)

        dict_relays = {}
        for i in relays_open:
            dict_relays[i] = False
        for i in relays_close:
            dict_relays[i] = True
        list_relays = list(dict_relays.items())

        self._infra.mp_remote.exec_raw(cmd=f"set_relays({list_relays})")

    @contextlib.contextmanager
    def relays_ctx(
        self,
        description: str,
        relays_close: list[int] | None = None,
        relays_open: list[int] | None = None,
    ) -> typing.Generator[None]:
        """
        closes/opens relays and finally to the inverted state.
        Important: The relais will not be set to the state it had prior. The will be set to the inverted state given by the parameters.
        """
        try:
            logger.debug(f"CTX enter: {description}")
            self.relays(relays_close=relays_close, relays_open=relays_open)
            yield None
        finally:
            logger.debug(f"CTX leave: {description}")
            self.relays(relays_close=relays_open, relays_open=relays_close)

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

        self.load_base_code()

        self._infra.mp_remote.exec_raw(
            cmd=f"set_relays_pulse(relays={relays}, initial_closed={initial_closed}, durations_ms={durations_ms})",
            timeout=int(1.5 * 1000 * sum(durations_ms)),
        )

    def _set_pin(self, name: str, on: bool) -> None:
        assert isinstance(on, bool)
        self.load_base_code()
        self._infra.mp_remote.exec_raw(cmd=f"{name}.value({int(on)})")

    def active_led(self, on: bool) -> None:
        self._set_pin("pin_led_active", on=on)

    def error_led(self, on: bool) -> None:
        self._set_pin("pin_led_error", on=on)

    def power_dut(self, on: bool) -> None:
        self._set_pin("pin_power_dut", on=on)

    def power_probe(self, on: bool) -> None:
        self._set_pin("pin_power_probe", on=on)

    def power_probeboot(self, on: bool) -> None:
        self._set_pin("pin_power_probeboot", on=on)

    def power_proberun(self, on: bool) -> None:
        self._set_pin("pin_power_proberun", on=on)
