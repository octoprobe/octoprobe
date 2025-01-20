"""
This thread will observe journalctl for some USB error message.
If one of these messages appear, the process will be exited.

To be able to use journalctl, the user has to:
sudo usermod -a -G systemd-journal octoprobe
"""

from __future__ import annotations

import logging
import os
import pathlib
import re
import shutil
import signal
import subprocess
import threading
import time

from .util_baseclasses import OctoprobeAppExitException

logger = logging.getLogger(__file__)


class JournalctlObserver:
    RE_ERRORS = [
        re.compile(r)
        for r in [
            r"MESSAGE=usb .*?: Not enough bandwidth for new device state",
            # Mon 2025-01-20 15:05:58.411543 CET [s=3c16c64ddc5e47d3860baf61bd03cdcb;i=f293a2;b=5431e12877f64e10b32eae46c739923e;m=2321b29f4;t=62c23c2786517;x=fbb7f5b297371ab4]
            #     _TRANSPORT=kernel
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            #     _MACHINE_ID=77fcb404e8b74dec85b578d4ad7ddb25
            #     _HOSTNAME=hans-Yoga-260
            #     _RUNTIME_SCOPE=system
            #     PRIORITY=4
            #     _KERNEL_SUBSYSTEM=usb
            #     _UDEV_SYSNAME=1-1.4.4.3
            #     MESSAGE=usb 1-1.4.4.3: Not enough bandwidth for new device state.
            #     _KERNEL_DEVICE=c189:122
            #     _UDEV_DEVNODE=/dev/bus/usb/001/123
            #     _BOOT_ID=5431e12877f64e10b32eae46c739923e
            #     _SOURCE_MONOTONIC_TIMESTAMP=9430621282
            r"MESSAGE=usb .*?: can't set config",
            # Mon 2025-01-20 15:05:58.411820 CET [s=3c16c64ddc5e47d3860baf61bd03cdcb;i=f293a3;b=5431e12877f64e10b32eae46c739923e;m=2321b2b09;t=62c23c278662c;x=2f39069dda9f5cb2]
            #     _TRANSPORT=kernel
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            #     _MACHINE_ID=77fcb404e8b74dec85b578d4ad7ddb25
            #     _HOSTNAME=hans-Yoga-260
            #     _RUNTIME_SCOPE=system
            #     PRIORITY=3
            #     _KERNEL_SUBSYSTEM=usb
            #     _UDEV_SYSNAME=1-1.4.4.3
            #     MESSAGE=usb 1-1.4.4.3: can't set config #1, error -28
            #     _KERNEL_DEVICE=c189:122
            #     _UDEV_DEVNODE=/dev/bus/usb/001/123
            #     _BOOT_ID=5431e12877f64e10b32eae46c739923e
            #     _SOURCE_MONOTONIC_TIMESTAMP=9430621300
        ]
    ]

    def __init__(self, logfile: pathlib.Path) -> None:
        self._logfile = logfile
        self._f_write = self._logfile.open("w")

        program = "journalctl"
        args = [
            program,
            "--facility=kern",
            "--priority=warning..emerg",
            "--no-hostname",
            "_KERNEL_SUBSYSTEM=usb",
            "--output=verbose",
            "--since=now",
            "--follow",
        ]

        self._f_write.write(" ".join(args))
        self._f_write.write("\n\n")
        self._f_write.write("USB warning will be appended below...\n")
        self._f_write.flush()
        self._f_read = self._logfile.open("r")
        self._f_read.read()
        self.proc = subprocess.Popen(
            args=args,
            executable=shutil.which(program),
            close_fds=True,
            text=True,
            stdout=self._f_write,
            stderr=subprocess.PIPE,
        )
        self.assert_no_warnings()

    def start_observer_thread(self) -> None:
        """
        This may be called from the main thread.
        If an error is seen in journalctl, an error is logged
        an the main thread killed.
        """

        def observer():
            while True:
                time.sleep(1)

                warning = self.get_warning()
                if warning is None:
                    continue

                logger.error(warning)
                os.kill(os.getpid(), signal.SIGTERM)

        observer_thread = threading.Thread(target=observer)
        observer_thread.daemon = True
        observer_thread.name = "journalctl observer"
        observer_thread.start()

    def get_warning(self) -> str | None:
        return_code = self.proc.poll()
        if return_code is not None:
            return f"journalctl has unexpectedly exited with: {self.proc.returncode}. See {self._logfile}"
        journal = self._f_read.read()
        if len(journal) == 0:
            return None
        logger.debug(f"journalctl: {journal}")
        for re_error in self.RE_ERRORS:
            for match in re_error.finditer(journal):
                return f"USB error '{match.group(0)}': See {self._logfile}"

        # forward = self._logfile.stat().st_size > self.f_pos:
        #     return f"USB errors: See {self._logfile}"
        return None

    def assert_no_warnings(self) -> None:
        """
        This may be called from the main thread
        """
        warning = self.get_warning()
        if warning is None:
            return
        logger.error(warning)
        raise OctoprobeAppExitException(warning)
