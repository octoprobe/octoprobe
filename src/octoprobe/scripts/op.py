from __future__ import annotations

import logging
import pathlib
import typing
from typing import Optional

import typer
import typing_extensions

from octoprobe.util_cached_git_repo import CachedGitRepo
from octoprobe.util_constants import DIRECTORY_OCTOPROBE_GIT_CACHE

from ..lib_tentacle_infra import TentacleInfra
from ..usb_tentacle.usb_constants import TyperPowerCycle, TyperUsbPlug
from ..usb_tentacle.usb_tentacle import UsbTentacle, UsbTentacles
from ..util_pyudev_monitor import do_udev_monitor
from . import op_bootmode, op_flash
from .commissioning import do_commissioning
from .op_exec_infra import do_exec_infra
from .op_install import URL_RELEASE_DEFAULT, do_install
from .op_logging import init_logging

# 'typer' does not work correctly with typing.Annotated
# Required is: typing_extensions.Annotated
TyperAnnotated = typing_extensions.Annotated

# mypy: disable-error-code="valid-type"
# This will disable this warning:
#   op.py:58: error: Variable "octoprobe.scripts.op.TyperAnnotated" is not valid as a type  [valid-type]
#   op.py:58: note: See https://mypy.readthedocs.io/en/stable/common_issues.html#variables-vs-type-aliases

app = typer.Typer()


_SerialsAnnotation = TyperAnnotated[
    Optional[list[str]],  # noqa: UP045
    typer.Option(help="Apply only to the selected tentacles"),
]
_ReposAnnotation = TyperAnnotated[
    Optional[list[str]],  # noqa: UP045
    typer.Option(help="Repos to be cloned"),
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


@app.command(help="Tests git clone/checkout functionality.")
def debug_git_checkout(
    repos: _ReposAnnotation = None, submodules: bool = False, debug: bool = False
) -> None:
    """ """
    init_logging(logging.DEBUG if debug else None)

    if repos is None:
        print("No repos specified...")
        return

    CachedGitRepo.clean_directory_work_repo(
        directory_cache=DIRECTORY_OCTOPROBE_GIT_CACHE
    )
    for idx, git_spec in enumerate(repos):
        repo_name = chr(idx + ord("A"))
        print(f"{repo_name} -> {git_spec}")
        git_repo = CachedGitRepo(
            directory_cache=DIRECTORY_OCTOPROBE_GIT_CACHE,
            git_spec=git_spec,
            prefix=f"{repo_name}_",
        )
        git_repo.clone(git_clean=True, submodules=submodules)
        repo_directory = git_repo.directory_git_work_repo
        print(f"{repo_directory}\n  {git_spec}\n")

    print("Done")


@app.command(help="Installs some binaries which require root rights.")
def install(url: str = URL_RELEASE_DEFAULT) -> None:
    """ """
    init_logging()
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
    line_delimiter: str | None = "",
) -> typing.Iterator[UsbTentacle]:
    """
    Query and select tentacles.
    Verbose iterate
    """
    init_logging()

    usb_tentacles = UsbTentacles.query(poweron=poweron)
    usb_tentacles = usb_tentacles.select(serials=serials)
    for usb_tentacle in usb_tentacles:
        print(usb_tentacle.label_long)
        yield usb_tentacle
        if line_delimiter is not None:
            print(line_delimiter)


@app.command(help="Power cycle usb ports.")
def powercycle(
    power_cycle: TyperPowerCycle,
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        tentacle_infra = TentacleInfra.factory_usb_tentacle(usb_tentacle=usb_tentacle)
        tentacle_infra.load_base_code_if_needed()
        tentacle_infra.switches.powercycle(power_cycle=power_cycle)


@app.command(help="Bring and PICO_INFRA into boot mode.")
def bootmode_infra(
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
    picotool_cmd: _PicotoolCmdAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        op_bootmode.do_bootmode(
            usb_tentacle=usb_tentacle, is_infra=True, picotool_cmd=picotool_cmd
        )


@app.command(help="Bring and PICO_PROBE into boot mode.")
def bootmode_probe(
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
    picotool_cmd: _PicotoolCmdAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        op_bootmode.do_bootmode(
            usb_tentacle=usb_tentacle,
            is_infra=False,
            picotool_cmd=picotool_cmd,
        )


@app.command(help="Flash firmware to PICO_INFRA.")
def flash_infra(
    firmware: pathlib.Path,
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        op_flash.do_flash(usb_tentacle=usb_tentacle, is_infra=True, firmware=firmware)


@app.command(help="Flash firmware to PICO_PROBE.")
def flash_probe(
    firmware: pathlib.Path,
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        op_flash.do_flash(usb_tentacle=usb_tentacle, is_infra=False, firmware=firmware)


@app.command(help="Execute micropython code on pico-infra.")
def exec_infra(
    code: TyperAnnotated[
        str,
        typer.Argument(help="Micropython code to execute on each pico-infra tentacle."),
    ] = "set_relays([(1, True)])",
    serials: _SerialsAnnotation = None,
    poweron: _PoweronAnnotation = False,
) -> None:
    for usb_tentacle in iter_usb_tentacles(poweron=poweron, serials=serials):
        ret = do_exec_infra(usb_tentacle=usb_tentacle, code=code)
        print(f"  {usb_tentacle.serial_delimited} '{code}' ==> '{ret}'")


@app.command(help="Power on/off usb ports.")
def power(
    on: TyperAnnotated[
        list[TyperUsbPlug] | None,  # noqa: UP007
        typer.Option(help="Power ON given usb hub port on all tentacles"),
    ] = None,
    off: TyperAnnotated[
        list[TyperUsbPlug] | None,  # noqa: UP007
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
    if on is None:
        on = []
    if off is None:
        off = []
    for usb_tentacle in iter_usb_tentacles(
        poweron=poweron,
        serials=serials,
        line_delimiter=op_bootmode.DELIM + "plugs.text",
    ):
        tentacle_infra = TentacleInfra.factory_usb_tentacle(usb_tentacle=usb_tentacle)
        plug: TyperUsbPlug
        for plug in on:
            tentacle_infra.handle_typer_usb_plug(typer_usb_plug=plug, on=True)
        for plug in off:
            tentacle_infra.handle_typer_usb_plug(typer_usb_plug=plug, on=False)


@app.command(help="Query connected tentacles.")
def query(poweron: _PoweronAnnotation = False) -> None:
    for usb_tentacle in iter_usb_tentacles(
        poweron=poweron,
        serials=None,
        line_delimiter=None,
    ):
        tentacle_infra = TentacleInfra.factory_usb_tentacle(usb_tentacle=usb_tentacle)
        tentacle_infra.load_base_code_if_needed()

        def log(label: str, value: str) -> bool:
            if value != "-":
                print(f"  {label}: {value}")
                return True
            return False

        log("hw_version", tentacle_infra.mcu_infra.hw_version)
        log("dut", usb_tentacle.usb_port_dut.device_text)
        ok = log("probe-appmode", usb_tentacle.usb_port_probe.device_text)
        if not ok:
            log("probe-progmode", usb_tentacle.usb_port_probe.usb_text)


if __name__ == "__main__":
    app()
