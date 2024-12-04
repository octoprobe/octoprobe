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

DIRECTORY_OCTOPROBE_CACHE_FIRMWARE = DIRECTORY_OCTOPROBE_DOWNLOADS / "cache_firmware"
DIRECTORY_OCTOPROBE_CACHE_FIRMWARE.mkdir(parents=True, exist_ok=True)
