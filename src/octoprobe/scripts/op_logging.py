import json
import logging
import logging.config
import pathlib

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
FILENAME_LOGGING_JSON = DIRECTORY_OF_THIS_FILE / "commissioning_logging.json"
assert FILENAME_LOGGING_JSON.is_file()


def init_logging() -> None:
    logging.config.dictConfig(json.loads(FILENAME_LOGGING_JSON.read_text()))
