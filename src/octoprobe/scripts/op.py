from __future__ import annotations

import typing
from typing import Optional

import typer
import typing_extensions

from ..usb_tentacle.usb_constants import (
    TyperPowerCycle,
    TyperUsbPlug,
    UsbPlugs,
)
from ..usb_tentacle.usb_tentacle import UsbTentacle, UsbTentacles
from ..util_pyudev_monitor import do_udev_monitor
from . import util_bootmode
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


_SerialsAnnotation = TyperAnnotated[
    Optional[list[str]],  # noqa: UP007
    typer.Option(help="Apply only to the selected tentacles"),
]

_PoweronAnnotation = TyperAnnotated[
    bool,
    typer.Option(
        help="If a PICO_INFRA is powered off, it will not be detected in a query. This option will detect all hubs and power on PICO_INFRA."
    ),
]

_PicotoolCmdAnnotation = TyperAnnotated[
    bool,
    typer.Option(help="Show the picotoolcommand."),
]


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


def iter_usb_tentacles(
    poweron: bool,
    serials: list[str] | None,
) -> typing.Iterator[UsbTentacle]:
    """
    Query and select tentacles.
    Verbose iterate
    """
    usb_tentacles = UsbTentacles.query(poweron=poweron)
    usb_tentacles = usb_tentacles.select(serials=serials)
    for usb_tentacle in usb_tentacles:
        print(usb_tentacle.label_long)
        yield usb_tentacle


@app.command(help="Power cycle usb ports.")
def powercycle(
    power_cycle: TyperPowerCycle,
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        usb_tentacle.powercycle(power_cycle=power_cycle)


@app.command(help="Bring and PICO_INFRA into boot mode.")
def bootmode_infra(
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
    picotool_cmd: _PicotoolCmdAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        util_bootmode.bootmode(
            usb_tentacle=usb_tentacle, is_infra=True, picotool_cmd=picotool_cmd
        )


@app.command(help="Bring and PICO_PROBE into boot mode.")
def bootmode_probe(
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
    picotool_cmd: _PicotoolCmdAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        util_bootmode.bootmode(
            usb_tentacle=usb_tentacle, is_infra=False, picotool_cmd=picotool_cmd
        )


@app.command(help="Power on/off usb ports.")
def power(
    on: TyperAnnotated[
        Optional[list[TyperUsbPlug]],  # noqa: UP007
        typer.Option(help="Power ON given usb hub port on all tentacles"),
    ] = None,
    off: TyperAnnotated[
        Optional[list[TyperUsbPlug]],  # noqa: UP007
        typer.Option(help="Power OFF given usb hub port on all tentacles"),
    ] = None,
    serials: _SerialsAnnotation = None,
    set_off: TyperAnnotated[
        bool,
        typer.Option(
            help="Power OFF ALL usb hub ports (except infraboot) on ALL tentacles"
        ),
    ] = False,
    poweron: _PoweronAnnotation = False,
) -> None:
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

    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        usb_tentacle.set_plugs(plugs)

        print(util_bootmode._DELIM + plugs.text)


@app.command(help="Query connected tentacles.")
def query(poweron: _PoweronAnnotation = False) -> None:
    for _ in iter_usb_tentacles(poweron=poweron, serials=None):
        pass


if __name__ == "__main__":
    app()
