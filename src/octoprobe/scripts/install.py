import json
import logging
import logging.config
import pathlib
import shutil
import tarfile
from urllib.request import urlretrieve

from .. import udev_placeholder
from ..util_constants import (
    DIRECTORY_OCTOPROBE_DOWNLOADS,
    DIRECTORY_OCTOPROBE_DOWNLOADS_BINARIES,
    DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN,
)

logger = logging.getLogger(__file__)

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
FILENAME_LOGGING_JSON = DIRECTORY_OF_THIS_FILE / "commissioning_logging.json"
assert FILENAME_LOGGING_JSON.is_file()


URL_RELEASE_DEFAULT = (
    "https://github.com/octoprobe/build_binaries/releases/latest/download/binaries.tgz"
)


def init_logging() -> None:
    logging.config.dictConfig(json.loads(FILENAME_LOGGING_JSON.read_text()))


def do_install(url: str) -> None:
    init_logging()

    logger.info(f"Binaries download from: {url}")

    tmp_filename, _headers = urlretrieve(url=url)

    shutil.rmtree(DIRECTORY_OCTOPROBE_DOWNLOADS_BINARIES, ignore_errors=True)
    DIRECTORY_OCTOPROBE_DOWNLOADS_BINARIES.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tmp_filename, mode="r") as f:
        f.extractall(DIRECTORY_OCTOPROBE_DOWNLOADS)

    _download_bossac()

    try:
        d = DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN.relative_to(pathlib.Path.home())
        dir_binaries_text = f"~/{d}"
        dir_binaries_home = f"$HOME/{d}"
    except ValueError:
        dir_binaries_text = str(DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN)
        dir_binaries_home = str(DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN)

    udev_path = pathlib.Path(udev_placeholder.__file__).parent.absolute() / "udev"
    cmd_echo = "echo 'PATH=" + dir_binaries_home + ":$PATH' >> ~/.profile"
    lines = [
        f"Binaries extracted to: {dir_binaries_text}",
        "Please apply the following commands:",
        f"  {cmd_echo}",
        f"  sudo cp {udev_path}/*.rules /etc/udev/rules.d",
        "  sudo sudo udevadm control --reload-rules",
        "  sudo sudo udevadm trigger",
    ]
    logger.info("\n".join(lines))


def _download_bossac() -> None:
    """
    See links here: https://github.com/arduino/BOSSA/releases/tag/1.9.1-arduino2
    """
    for url_sub, directory_sub in (
        ("linux64", "x86_64"),
        ("linuxaarch64", "aarch64"),
    ):
        url = (
            f"http://downloads.arduino.cc/tools/bossac-1.9.1-arduino2-{url_sub}.tar.gz"
        )

        # logger.info(f"Binaries download from: {url}")

        tmp_filename, _headers = urlretrieve(url=url)
        with tarfile.open(tmp_filename, mode="r") as f:
            fin = f.extractfile(member="bin/bossac")
            filename = (
                DIRECTORY_OCTOPROBE_DOWNLOADS / "binaries" / directory_sub / "bossac"
            )
            assert fin is not None
            filename.write_bytes(fin.read())
            filename.chmod(0o755)
