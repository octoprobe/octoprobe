import contextlib
import json
import logging
import logging.config
import pathlib

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
FILENAME_LOGGING_JSON = DIRECTORY_OF_THIS_FILE / "util_logging_config.json"

FORMATTER = logging.Formatter("%(levelname)-8s - %(message)s")
ROOT_LOGGER = logging.getLogger()


def init_logging() -> None:
    logging.config.dictConfig(json.loads(FILENAME_LOGGING_JSON.read_text()))


@contextlib.contextmanager
def log(directory: pathlib.Path, name: str, level: int) -> None:
    """
    Write logging to logfile
    """

    handler = logging.FileHandler(directory / f"logger_{level}_{name}.log", mode="w")
    handler.level = level
    handler.formatter = FORMATTER
    ROOT_LOGGER.addHandler(handler)
    yield
    ROOT_LOGGER.removeHandler(handler)


@contextlib.contextmanager
def logs(directory: pathlib.Path) -> None:
    """
    Write logging to logfile
    """
    assert isinstance(directory, pathlib.Path)

    with (
        log(directory, "error", logging.ERROR),
        log(directory, "info", logging.INFO),
        log(directory, "debug", logging.DEBUG),
    ):
        yield
