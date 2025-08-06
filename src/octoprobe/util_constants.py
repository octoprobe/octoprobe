import enum
import os
import pathlib

DELIMITER_SERIAL_BOARD = "-"
"""
Example: 1831-RPI_PICO
"""

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

ENV_OCTOPROBE_DOWNLOADS = "OCTOPROBE_DOWNLOADS"
try:
    DIRECTORY_OCTOPROBE_DOWNLOADS = pathlib.Path(os.environ[ENV_OCTOPROBE_DOWNLOADS])
except KeyError:
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


class DirectoryTag(enum.StrEnum):
    """
    These tags will be used to reference the different directories.
    """

    F = "F"
    # Firmware Source Git Repo
    R = "R"
    # Results (Testresults direcory)
    T = "T"
    # Tests Source Git Repo
    P = "P"
    # Python venv directory
    W = "W"
    # Working directory

    def description(self) -> str:
        return {
            DirectoryTag.F: "Firmware Source Git Repo",
            DirectoryTag.R: "Results",
            DirectoryTag.T: "Tests Source Git Repo",
            DirectoryTag.P: "Python venv directory",
            DirectoryTag.W: "Working directory",
        }[self]

    def render(self, filename: pathlib.Path) -> str:
        """
        Expects 'filename' to be a relative path!

        Return: [W]src/octoprobe/util_constants.py
        """
        assert isinstance(filename, pathlib.Path)
        assert not filename.is_absolute()
        return f"[{self.name}]{filename}"

    def render_relative_to(self, top: pathlib.Path, filename: pathlib.Path) -> str:
        """
        Converts filename to a relative path if possible and adds the directory tag.
        If filename is below top:
          [W]src/octoprobe/util_constants.py
        else:
          /home/xy/src/octoprobe/util_constants.py
        """
        assert isinstance(top, pathlib.Path)
        assert isinstance(filename, pathlib.Path)
        # Fallback to absolute pathnames
        return str(filename)
        try:
            return self.render(filename.relative_to(top))
        except ValueError:
            return str(filename)


class ExitCode(enum.IntEnum):
    """
    Exit Codes similar to: https://docs.pytest.org/en/stable/reference/exit-codes.html
    """

    SUCCESS = 0
    "All tests succeeded"
    FAILURE = 1
    "At least one test failed: Need to have a look at the reports."
    ERROR = 2
    "At least one test returned an error: Need to have a look at the reports."


def relative_cwd(filename: pathlib.Path) -> str:
    """
    Return the path to the filename relative to the current working directory.
    Return the full path If filename is outside of the current directory.
    """
    return DirectoryTag.W.render_relative_to(top=pathlib.Path.cwd(), filename=filename)


def main() -> None:
    print(relative_cwd(pathlib.Path(__file__)))
    print(relative_cwd(pathlib.Path.cwd() / "x" / "y.txt"))
    print(relative_cwd(pathlib.Path("/tmp/x")))


if __name__ == "__main__":
    main()
