from __future__ import annotations

from typing import Optional

import typer
import typing_extensions

from .. import util_usb_serial
from ..util_power import PowerCycle, UsbPlug, UsbPlugs
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
    power_cycle: PowerCycle,
    serial: TyperAnnotated[Optional[list[str]], typer.Option()] = None,  # noqa: UP007
) -> None:
    hubs = util_usb_serial.QueryResultTentacle.query(verbose=serial is not None)
    hubs = hubs.select(serials=serial)
    hubs.powercycle(power_cycle=power_cycle)


@app.command(help="Power on/off usb ports.")
def power(
    on: TyperAnnotated[Optional[list[UsbPlug]], typer.Option()] = None,  # noqa: UP007
    off: TyperAnnotated[Optional[list[UsbPlug]], typer.Option()] = None,  # noqa: UP007
    serial: TyperAnnotated[Optional[list[str]], typer.Option()] = None,  # noqa: UP007
    set_off: TyperAnnotated[bool, typer.Option()] = False,
) -> None:
    hubs = util_usb_serial.QueryResultTentacle.query(verbose=serial is not None)
    hubs = hubs.select(serials=serial)

    plugs = UsbPlugs()
    if set_off:
        plugs.set_default_off()
    if on is not None:
        for _on in on:
            plugs.plugs[_on] = True
    if off is not None:
        for _off in off:
            plugs.plugs[_off] = False
    hubs.set_power(plugs)

    print(plugs.text)


@app.command(help="Query connected tentacles.")
def query(
    verbose: TyperAnnotated[bool, typer.Option()] = True,
) -> None:
    hubs = typer_query.Query(verbose=verbose)
    hubs.print()


if __name__ == "__main__":
    app()
