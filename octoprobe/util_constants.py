import pathlib

TAG_BOARD = "board"
TAG_PROGRAMMER = "programmer"
TAG_MCU = "mcu"

DIRECTORY_OCTOPROBE_DOWNLOADS = pathlib.Path.home() / "octoprobe_downloads"
DIRECTORY_OCTOPROBE_DOWNLOADS.mkdir(parents=True, exist_ok=True)
assert DIRECTORY_OCTOPROBE_DOWNLOADS.is_dir()

DIRECTORY_OCTOPROBE_CACHE_FIRMWARE = DIRECTORY_OCTOPROBE_DOWNLOADS / "cache_firmware"
DIRECTORY_OCTOPROBE_CACHE_FIRMWARE.mkdir(parents=True, exist_ok=True)

DIRECTORY_USR_SBIN = pathlib.Path("/usr/sbin")
assert DIRECTORY_USR_SBIN.is_dir()
