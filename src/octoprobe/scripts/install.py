import json
import logging
import logging.config
import os
import pathlib
import shutil
import tarfile
from urllib.request import urlretrieve

from ..util_constants import DIRECTORY_OCTOPROBE_DOWNLOADS

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

    directory_binaries = DIRECTORY_OCTOPROBE_DOWNLOADS / "binaries"
    shutil.rmtree(directory_binaries, ignore_errors=True)
    directory_binaries.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tmp_filename, mode="r") as f:
        f.extractall(DIRECTORY_OCTOPROBE_DOWNLOADS)

    try:
        d = directory_binaries.relative_to(pathlib.Path.home())
        dir_binaries_text = f"~/{d}"
        dir_binaries_home = f"$HOME/{d}"
    except ValueError:
        dir_binaries_text = str(directory_binaries)
        dir_binaries_home = str(directory_binaries)
    binaries_machine_text = f"{dir_binaries_text}/{os.uname().machine}/*"
    binaries_machine_home = f"{dir_binaries_home}/{os.uname().machine}"
    lines = [
        f"Binaries extracted to: {dir_binaries_text}",
        "Please install the files as follows",
        f"sudo chown root:root {binaries_machine_text}",
        f"sudo chmod a+s {binaries_machine_text}",
        f"""echo 'PATH="{binaries_machine_home}:$PATH"' >> ~/.profile""",
    ]
    logger.info("\n".join(lines))

    _do_install_bossac()


def _do_install_bossac() -> None:
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
