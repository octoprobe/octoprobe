import pathlib

TAG_BOARD = "board"
TAG_PROGRAMMER = "programmer"
TAG_MCU = "mcu"

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent

DIRECTORY_DOWNLOADS = DIRECTORY_OF_THIS_FILE / "downloads"
assert DIRECTORY_DOWNLOADS.is_dir()

DIRECTORY_CACHE_FIRMWARE = DIRECTORY_DOWNLOADS / "cache_firmware"
DIRECTORY_CACHE_FIRMWARE.mkdir(parents=True, exist_ok=True)
