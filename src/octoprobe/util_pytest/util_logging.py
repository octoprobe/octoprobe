import json
import logging
import logging.config
import pathlib

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
FILENAME_LOGGING_JSON = DIRECTORY_OF_THIS_FILE / "util_logging_config.json"

FORMATTER = logging.Formatter("%(levelname)-8s - %(message)s")
ROOT_LOGGER = logging.getLogger()
logger = logging.getLogger(__file__)


def init_logging() -> None:
    logging.config.dictConfig(json.loads(FILENAME_LOGGING_JSON.read_text()))

    # https://code.activestate.com/recipes/577074-logging-asserts/
    # def excepthook(*args):
    #     logger.error("Uncaught exception:", exc_info=args)

    # sys.excepthook = excepthook


class Log:
    def __init__(self, directory: pathlib.Path, name: str, level: int) -> None:
        """
        Create a logfile.
        Add a logging handler and eventually remove it again.
        """
        self._handler: logging.FileHandler | None = logging.FileHandler(
            directory / f"logger_{level}_{name}.log", mode="w"
        )
        self._handler.level = level
        self._handler.formatter = FORMATTER
        ROOT_LOGGER.addHandler(self._handler)

    def remove(self) -> None:
        if self._handler is None:
            return
        ROOT_LOGGER.removeHandler(self._handler)
        self._handler = None

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.remove()


class Logs:
    def __init__(self, directory: pathlib.Path) -> None:
        """
        Create three logfiles (error, info, debug) to the given directory.
        Add logging handlers and eventually remove them again.
        """
        assert isinstance(directory, pathlib.Path)

        self._handlers = [
            Log(directory, "error", logging.ERROR),
            Log(directory, "info", logging.INFO),
            Log(directory, "debug", logging.DEBUG),
        ]

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        for handler in self._handlers:
            handler.remove()
