"""
This does something similar as: udevadm monitor -p
"""

import time

import pyudev

from .util_pyudev import get_device_debug


def do_udev_monitor() -> None:
    def callback(device_event: pyudev.Device):
        print(get_device_debug(device_event=device_event, subsystem_filtered="block"))

    print("Monitoring tty, usb and block events...")
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="tty")
    monitor.filter_by(subsystem="usb", device_type="usb_device")
    monitor.filter_by(subsystem="block", device_type="disk")
    observer = pyudev.MonitorObserver(monitor, callback=callback)
    observer.start()
    while True:
        time.sleep(60)


if __name__ == "__main__":
    do_udev_monitor()
