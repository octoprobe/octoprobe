from __future__ import annotations

from typing import Optional

import typer
import typing_extensions

from octoprobe.usb_tentacle.usb_tentacle import UsbTentacles

from ..usb_tentacle.usb_constants import TyperPowerCycle, TyperUsbPlug, UsbPlugs
from ..util_pyudev_monitor import do_udev_monitor
from . import typer_query
from .commissioning import do_commissioning
from .install import URL_RELEASE_DEFAULT, do_install

# 'typer' does not work correctly with typing.Annotated
# Required is: typing_extensions.Annotated
TyperAnnotated = typing_extensions.Annotated

# mypy: disable-error-code="valid-type"
# This will disable this warning:
#   op.py:58: error: Variable "octoprobe.scripts.op.TyperAnnotated" is not valid as a type  [valid-type]
#   op.py:58: note: See https://mypy.readthedocs.io/en/stable/common_issues.html#variables-vs-type-aliases

app = typer.Typer()


@app.command(help="Installs some binaries which require root rights.")
def install(url: str = URL_RELEASE_DEFAULT) -> None:
    """ """
    do_install(url=url)


@app.command(help="Monitors udev events. This is helpful for debugging.")
def udev() -> None:
    """ """
    do_udev_monitor()


@app.command(help="Use this command to test new tentacles")
def commissioning() -> None:
    """ """
    do_commissioning()


@app.command(help="Power cycle usb ports.")
def powercycle(
    power_cycle: TyperPowerCycle,
    serial: TyperAnnotated[Optional[list[str]], typer.Option()] = None,  # noqa: UP007
) -> None:
    usb_tentacles = UsbTentacles.query(require_serial=serial is not None)
    usb_tentacles = usb_tentacles.select(serials=serial)
    usb_tentacles.powercycle(power_cycle=power_cycle)


@app.command(help="Power on/off usb ports.")
def power(
    on: TyperAnnotated[Optional[list[TyperUsbPlug]], typer.Option()] = None,  # noqa: UP007
    off: TyperAnnotated[Optional[list[TyperUsbPlug]], typer.Option()] = None,  # noqa: UP007
    serial: TyperAnnotated[Optional[list[str]], typer.Option()] = None,  # noqa: UP007
    set_off: TyperAnnotated[bool, typer.Option()] = False,
) -> None:
    usb_tentacles = UsbTentacles.query(require_serial=serial is not None)
    usb_tentacles = usb_tentacles.select(serials=serial)

    _on = TyperUsbPlug.convert(on)
    _off = TyperUsbPlug.convert(off)

    plugs = UsbPlugs()
    if set_off:
        plugs = UsbPlugs.default_off()
    if _on is not None:
        for __on in _on:
            plugs[__on] = True
    if _off is not None:
        for __off in _off:
            plugs[__off] = False
    usb_tentacles.set_plugs(plugs)

    print(plugs.text)


@app.command(help="Query connected tentacles.")
def query(
    verbose: TyperAnnotated[bool, typer.Option()] = True,
) -> None:
    hubs = typer_query.Query(verbose=verbose)
    hubs.print()


if __name__ == "__main__":
    app()
