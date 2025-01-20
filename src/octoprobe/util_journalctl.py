from __future__ import annotations

import logging
import pathlib
import subprocess

from .util_baseclasses import OctoprobeAppExitException

logger = logging.getLogger(__file__)


class JournalctlObserver:
    def __init__(self, logfile: pathlib.Path) -> None:
        self.logfile = logfile
        self.f = self.logfile.open("w")

        args = [
            "journalctl",
            "--facility=kern",
            "--priority=warning..emerg",
            "--no-hostname",
            "_KERNEL_SUBSYSTEM=usb",
            "--output=verbose",
            "--since=now",
            "--follow",
        ]

        self.f.write(" ".join(args))
        self.f.write("\n\n")
        self.f_pos = self.f.tell()
        self.proc = subprocess.run(
            args=args,
            check=False,
            text=True,
            # Specific args
            stdout=self.f,
            stderr=subprocess.STDOUT,
        )

    def start_observer_thread(self) -> None:
        pass

    def assert_no_warnings(self) -> None:
        if self.logfile.stat().st_size <= self.f_pos:
            return
        msg = f"USB errors: See {self.logfile}"
        logger.error(msg)
        raise OctoprobeAppExitException(msg)
