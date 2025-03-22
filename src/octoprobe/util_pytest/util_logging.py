from __future__ import annotations

import json
import logging
import logging.config
import pathlib

from octoprobe.util_pytest.util_logging_handler_color import ColorFormatter

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
FILENAME_LOGGING_JSON = DIRECTORY_OF_THIS_FILE / "util_logging_config.json"

FORMAT = "%(levelname)-8s - %(message)s"
FORMATTER = logging.Formatter(FORMAT)
COLOR_FORMATTER = ColorFormatter(FORMAT)
ROOT_LOGGER = logging.getLogger()

logger = logging.getLogger(__file__)


def init_logging() -> None:
    logging.config.dictConfig(json.loads(FILENAME_LOGGING_JSON.read_text()))

    # https://code.activestate.com/recipes/577074-logging-asserts/
    # def excepthook(*args):
    #     logger.error("Uncaught exception:", exc_info=args)

    # sys.excepthook = excepthook


class Log:
    def __init__(
        self,
        directory: pathlib.Path,
        name: str,
        level: int,
        file_extension: str = "log",
        formatter: logging.Formatter = FORMATTER,
    ) -> None:
        """
        Create a logfile.
        Add a logging handler and eventually remove it again.
        """
        self.filename = directory / f"logger_{level}_{name}.{file_extension}"
        self._handler: logging.FileHandler | None = logging.FileHandler(
            self.filename, mode="w"
        )
        self._handler.level = level
        self._handler.formatter = formatter
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

        self._handlers = []
        for name, level in (
            ("error", logging.ERROR),
            ("info", logging.INFO),
            ("debug", logging.DEBUG),
        ):
            for formatter, file_extension in (
                (FORMATTER, "log"),
                (COLOR_FORMATTER, "color"),
            ):
                self._handlers.append(
                    Log(
                        directory,
                        name=name,
                        level=level,
                        formatter=formatter,
                        file_extension=file_extension,
                    )
                )

    @property
    def filename(self) -> pathlib.Path:
        return self._handlers[1].filename

    def __enter__(self) -> Logs:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        for handler in self._handlers:
            handler.remove()


def main() -> None:
    init_logging()

    logger.info("Color Test")
    logger.info("[COLOR_INFO]COLOR_INFO")
    logger.info("[COLOR_SUCCESS]COLOR_SUCCESS")
    logger.info("[COLOR_FAIL]COLOR_FAIL")
    logger.info("[COLOR_ERROR]COLOR_ERROR")


if __name__ == "__main__":
    main()
