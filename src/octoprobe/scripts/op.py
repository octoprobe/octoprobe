from __future__ import annotations

import time
from typing import Optional

import typer
import typing_extensions

from .. import util_mcu_rp2
from ..usb_tentacle.usb_constants import (
    TyperPowerCycle,
    TyperUsbPlug,
    UsbPlug,
    UsbPlugs,
)
from ..usb_tentacle.usb_tentacle import UsbTentacle, UsbTentacles
from ..util_pyudev import UdevPoller
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


_SerialAnnotation = TyperAnnotated[
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


@app.command(help="Power cycle usb ports.")
def powercycle(
    power_cycle: TyperPowerCycle,
    serial: TyperAnnotated[
        Optional[list[str]],  # noqa: UP007
        typer.Option(help="The serial number to be powercycled"),
    ] = None,
    poweron: _PoweronAnnotation = False,
) -> None:
    usb_tentacles = UsbTentacles.query(poweron=poweron)
    usb_tentacles = usb_tentacles.select(serials=serial)
    usb_tentacles.powercycle(power_cycle=power_cycle)


def _bootmode(usb_tentacle: UsbTentacle, is_infra: bool, picotool_cmd: bool) -> None:
    if usb_tentacle.rp2_infra.serial is None:
        print("Tentacle is already in boot mode. Please unconnect and reconnect USB.")
        return

    print("Press Boot Button.")
    print("Power off PICO_INFRA and PICO_PROBE.")
    usb_tentacle.set_plugs(
        plugs=UsbPlugs(
            {
                UsbPlug.INFRA: False,
                UsbPlug.PROBE: False,
                UsbPlug.DUT: False,
                UsbPlug.INFRABOOT: False,
            }
        )
    )

    time.sleep(0.1)

    with UdevPoller() as guard:
        print("Power on PICO_INFRA and PICO_PROBE.")
        usb_tentacle.set_plugs(
            plugs=UsbPlugs(
                {
                    UsbPlug.INFRA: True,
                    UsbPlug.PROBE: True,
                }
            )
        )
        time.sleep(0.2)
        print("Release Boot Button")
        usb_tentacle.set_plugs(
            plugs=UsbPlugs(
                {
                    UsbPlug.INFRABOOT: True,
                }
            )
        )

        rp2 = usb_tentacle.rp2_infra if is_infra else usb_tentacle.rp2_probe
        tag = "PICO_INFRA" if is_infra else "PICO_PROBE"
        assert rp2 is not None

        if picotool_cmd:
            udev_filter = util_mcu_rp2.rp2_udev_filter_boot_mode(
                util_mcu_rp2.RPI_PICO_USB_ID.boot,
                usb_location=rp2.location.short,
            )
        else:
            udev_filter = util_mcu_rp2.rp2_udev_filter_boot_mode2(
                util_mcu_rp2.RPI_PICO_USB_ID.boot,
                usb_location=rp2.location.short,
            )
        event = guard.expect_event(
            udev_filter=udev_filter,
            text_where=f"Tentacle with serial {usb_tentacle.serial}",
            text_expect=f"Expect {tag} in programming mode to become visible on udev after power on",
            timeout_s=10.0,
        )
        if picotool_cmd:
            assert isinstance(event, util_mcu_rp2.Rp2UdevBootModeEvent)
            picotool = util_mcu_rp2.picotool_cmd(
                event=event,
                filename_firmware="firmware.uf2",
            )
            picotool_text = " ".join(picotool)
            print(
                f"{usb_tentacle.serial}: Detected {tag} on port {rp2.location.short}."
            )
            print("Please use:")
            print("  " + picotool_text)
        else:
            assert isinstance(event, util_mcu_rp2.Rp2UdevBootModeEvent2)
            print(
                f"{usb_tentacle.serial}: Detected {tag} on port {rp2.location.short}."
            )
            print("Please use:")
            print("  " + f"cp firmware.uf2 {event.mount_point}")


@app.command(help="Bring and PICO_INFRA into boot mode.")
def bootmode_infra(
    serial: _SerialAnnotation = None,
    poweron: _PoweronAnnotation = False,
    picotool_cmd: _PicotoolCmdAnnotation = False,
) -> None:
    usb_tentacles = UsbTentacles.query(poweron=poweron)
    usb_tentacles = usb_tentacles.select(serials=serial)
    # usb_tentacles.set_plugs(plugs=UsbPlugs.default_off())
    for usb_tentacle in usb_tentacles:
        _bootmode(usb_tentacle=usb_tentacle, is_infra=True, picotool_cmd=picotool_cmd)


@app.command(help="Bring and PICO_PROBE into boot mode.")
def bootmode_probe(
    serial: _SerialAnnotation = None,
    poweron: _PoweronAnnotation = False,
    picotool_cmd: _PicotoolCmdAnnotation = False,
) -> None:
    usb_tentacles = UsbTentacles.query(poweron=poweron)
    usb_tentacles = usb_tentacles.select(serials=serial)
    # usb_tentacles.set_plugs(plugs=UsbPlugs.default_off())
    for usb_tentacle in usb_tentacles:
        _bootmode(usb_tentacle=usb_tentacle, is_infra=False, picotool_cmd=picotool_cmd)


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
    serial: _SerialAnnotation = None,
    set_off: TyperAnnotated[
        bool,
        typer.Option(
            help="Power OFF ALL usb hub ports (except infraboot) on ALL tentacles"
        ),
    ] = False,
) -> None:
    usb_tentacles = UsbTentacles.query(poweron=False)
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
def query(poweron: _PoweronAnnotation = False) -> None:
    hubs = typer_query.Query(poweron=poweron)
    hubs.print()


if __name__ == "__main__":
    app()
