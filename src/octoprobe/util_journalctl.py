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
            #     _BOOT_ID=5431e12877f64e10b32eae46c739923e
            #     _HOSTNAME=hans-Yoga-260
            #     _KERNEL_DEVICE=c189:122
            #     _KERNEL_SUBSYSTEM=usb
            #     _MACHINE_ID=77fcb404e8b74dec85b578d4ad7ddb25
            #     _RUNTIME_SCOPE=system
            #     _SOURCE_MONOTONIC_TIMESTAMP=9430621282
            #     _TRANSPORT=kernel
            #     _UDEV_DEVNODE=/dev/bus/usb/001/123
            #     _UDEV_SYSNAME=1-1.4.4.3
            #     MESSAGE=usb 1-1.4.4.3: Not enough bandwidth for new device state.
            #     PRIORITY=4
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            r"MESSAGE=usb .*?: can't set config",
            # Mon 2025-01-20 15:05:58.411820 CET [s=3c16c64ddc5e47d3860baf61bd03cdcb;i=f293a3;b=5431e12877f64e10b32eae46c739923e;m=2321b2b09;t=62c23c278662c;x=2f39069dda9f5cb2]
            #     _BOOT_ID=5431e12877f64e10b32eae46c739923e
            #     _HOSTNAME=hans-Yoga-260
            #     _KERNEL_DEVICE=c189:122
            #     _KERNEL_SUBSYSTEM=usb
            #     _MACHINE_ID=77fcb404e8b74dec85b578d4ad7ddb25
            #     _RUNTIME_SCOPE=system
            #     _SOURCE_MONOTONIC_TIMESTAMP=9430621300
            #     _TRANSPORT=kernel
            #     _UDEV_DEVNODE=/dev/bus/usb/001/123
            #     _UDEV_SYSNAME=1-1.4.4.3
            #     MESSAGE=usb 1-1.4.4.3: can't set config #1, error -28
            #     PRIORITY=3
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            r"MESSAGE=TODO...",
            # 2025-07-17: provoked by the ARDUINO_NANO_33_BLE_SENSE
            # Thu 2025-07-17 21:48:27.298561 CEST [s=4ede5dd1820f435db5f6a683258a4ba2;i=bb1c29;b=3f0a46b15471433b89b4b500f965ca1f;m=38db83f3d;t=63a254b084701;x=ecf2c6215f79e9aa]
            #     _MACHINE_ID=7eb3b265d30d4b448a1afd26defdf766
            #     _HOSTNAME=maerki-ideapad-320
            #     _RUNTIME_SCOPE=system
            #     _TRANSPORT=kernel
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            #     PRIORITY=3
            #     _KERNEL_SUBSYSTEM=usb
            #     _KERNEL_DEVICE=c189:301
            #     _UDEV_DEVNODE=/dev/bus/usb/003/046
            #     _UDEV_SYSNAME=3-7.3.1.3
            #     MESSAGE=usb 3-7.3.1.3: can't set config #1, error -32
            #     _BOOT_ID=3f0a46b15471433b89b4b500f965ca1f
            #     _SOURCE_BOOTTIME_TIMESTAMP=15262594760
            #     _SOURCE_MONOTONIC_TIMESTAMP=15262594760
            r"MESSAGE=usb .*?: reset high-speed USB device number",
            r"MESSAGE=usb .*?: attempt power cycle",
            # Fri 2025-01-31 19:05:29.974116 CET [s=4ede5dd1820f435db5f6a683258a4ba2;i=820253;b=0c3168bbe06541a5a92be924dde8ae39;m=70c5d2d19;t=62d0463562964;x=8cc213e2058364b2]
            #     _TRANSPORT=kernel
            #     PRIORITY=6
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            #     _BOOT_ID=0c3168bbe06541a5a92be924dde8ae39
            #     _MACHINE_ID=7eb3b265d30d4b448a1afd26defdf766
            #     _HOSTNAME=maerki-ideapad-320
            #     _RUNTIME_SCOPE=system
            #     _KERNEL_SUBSYSTEM=usb
            #     _KERNEL_DEVICE=c189:323
            #     _UDEV_DEVNODE=/dev/bus/usb/003/000
            #     _UDEV_SYSNAME=3-1.1.4
            #     _SOURCE_MONOTONIC_TIMESTAMP=30272105414
            #     MESSAGE=usb 3-1.1.4: reset high-speed USB device number 68 using xhci_hcd
            # MISSING: _KERNEL_SUBSYSTEM=usb
            # Fri 2025-01-31 19:05:30.263733 CET [s=4ede5dd1820f435db5f6a683258a4ba2;i=820255;b=0c3168bbe06541a5a92be924dde8ae39;m=70c61986b;t=62d04635a94b5;x=f0139dbcb79be972]
            #     _TRANSPORT=kernel
            #     PRIORITY=6
            #     SYSLOG_FACILITY=0
            #     SYSLOG_IDENTIFIER=kernel
            #     _BOOT_ID=0c3168bbe06541a5a92be924dde8ae39
            #     _MACHINE_ID=7eb3b265d30d4b448a1afd26defdf766
            #     _HOSTNAME=maerki-ideapad-320
            #     _RUNTIME_SCOPE=system
            #     MESSAGE=usb 3-1.1.4-port1: attempt power cycle
            #     _SOURCE_MONOTONIC_TIMESTAMP=30272395116
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
        self._f_write.write("USB warnings will be appended below...\n")
        self._f_write.flush()
        self._f_read = self._logfile.open("r")
        self._f_read.read()
        self.proc = subprocess.Popen(  # pylint: disable=consider-using-with
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
