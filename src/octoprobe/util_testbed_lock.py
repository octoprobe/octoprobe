"""
Create a lockfile 'testbed.lock' which prevents multiple octoprobe instances to run.

This typically happens in VSCode: While one instance is testing another instance - the pytest explorer - does 'collect-only'.
"""

import fcntl
import os
import pathlib


class TestbedLock:
    """
    See also: https://github.com/tox-dev/filelock
    """

    def __init__(self) -> None:
        self._lockfile: pathlib.Path | None = None
        self._fd: int = -1
        """
        This variable will avoid the cleanup by the garbage collector.
        """

    def acquire(self, filename: pathlib.Path) -> None:
        """
        Will throw an exception if the testbed is already locked.
        """
        self._fd = os.open(filename, os.O_CREAT | os.O_RDWR | os.O_TRUNC)
        self._lockfile = filename
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError(f"Testbed is already used! See: {filename}") from exc
        os.write(self._fd, f"Testinfrastructure locked by pid {os.getpid()}\n".encode())

    def unlink(self):
        if self._fd != -1:
            os.close(self._fd)
        if self._lockfile is not None:
            self._lockfile.unlink()