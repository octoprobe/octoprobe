import os
import pathlib

TAG_PROGRAMMER = "programmer"

TAG_BOARDS = "boards"
"""
For micropython, this corresponds to a 'board',
eg. RPI_PICO2 in https://github.com/micropython/micropython/tree/master/ports/rp2/boards/RPI_PICO2
"""

TAG_MCU = "mcu"
"""
For micropython, this corresponds to a 'port',
eg. a subdirectory of https://github.com/micropython/micropython/tree/master/ports
"""

DIRECTORY_OCTOPROBE_DOWNLOADS = pathlib.Path.home() / "octoprobe_downloads"
DIRECTORY_OCTOPROBE_DOWNLOADS.mkdir(parents=True, exist_ok=True)
assert DIRECTORY_OCTOPROBE_DOWNLOADS.is_dir()

DIRECTORY_OCTOPROBE_DOWNLOADS_BINARIES = DIRECTORY_OCTOPROBE_DOWNLOADS / "binaries"
DIRECTORY_OCTOPROBE_DOWNLOADS_MACHINE_BIN = (
    DIRECTORY_OCTOPROBE_DOWNLOADS_BINARIES / os.uname().machine
)

DIRECTORY_OCTOPROBE_CACHE_FIRMWARE = DIRECTORY_OCTOPROBE_DOWNLOADS / "firmware-cache"
DIRECTORY_OCTOPROBE_CACHE_FIRMWARE.mkdir(parents=True, exist_ok=True)
assert DIRECTORY_OCTOPROBE_CACHE_FIRMWARE.is_dir()

DIRECTORY_OCTOPROBE_GIT_CACHE = DIRECTORY_OCTOPROBE_DOWNLOADS / "git-cache"
DIRECTORY_OCTOPROBE_GIT_CACHE.mkdir(parents=True, exist_ok=True)
assert DIRECTORY_OCTOPROBE_GIT_CACHE.is_dir()


def relative_cwd(filename: pathlib.Path) -> pathlib.Path:
    """
    Return the path to the filename relative to the current working directory.
    Return the full path If filename is outside of the current directory.
    """
    try:
        return filename.relative_to(pathlib.Path.cwd())
    except ValueError:
        return filename
