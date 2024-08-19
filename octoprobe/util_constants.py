import pathlib

TAG_BOARD = "board"
TAG_PROGRAMMER = "programmer"
TAG_MCU = "mcu"

DIRECTORY_DOWNLOADS = pathlib.Path.home() / "octoprobe_downloads"
DIRECTORY_DOWNLOADS.mkdir(parents=True, exist_ok=tuple)
assert DIRECTORY_DOWNLOADS.is_dir()

DIRECTORY_CACHE_FIRMWARE = DIRECTORY_DOWNLOADS / "cache_firmware"
DIRECTORY_CACHE_FIRMWARE.mkdir(parents=True, exist_ok=True)

DIRECTORY_USR_SBIN = pathlib.Path("/usr/sbin")
assert DIRECTORY_USR_SBIN.is_dir()
