from __future__ import annotations

import abc
import dataclasses
import logging
import pathlib
import re
import select
import syslog
import time
from collections.abc import Iterator
from typing import Any, Self

import pyudev

logger = logging.getLogger(__file__)


_RE_USB_LOCATION = re.compile(r".*/(?P<location>\d+-\d+(\.\d+)*)")
"""
Input:
    /sys/devices/pci0000:00/0000:00:14.0/usb3/3-5/3-5.2/3-5.2.3/3-5.2.3:1.0/ttyACM1
    /sys/devices/pci0000:00/0000:00:14.0/usb3/3-5/3-5.2/3-5.2.3/3-5.2.3:1.1
    /sys/devices/pci0000:00/0000:00:14.0/usb3/3-5/3-5.2/3-5.2.3/3-5.2.3:1.0/tty/ttyACM
    /sys/devices/pci0000:00/0000:00:14.0/usb3/3-5/3-5.2/3-5.2.3
    /sys/devices/pci0000:00/0000:00:14.0/usb3/3-1
match:3-5.2.3
"""


class UdevFailException(Exception):
    pass


class UdevTimoutException(Exception):
    pass


class UdevEventBase(abc.ABC):
    @abc.abstractmethod
    def __init__(self, device: pyudev.Device): ...


_TIMEOUT_MOUNT_S = 5.0


def get_device_debug(device: pyudev.Device, subsystem_filtered: str) -> str:
    assert isinstance(device, pyudev.Device)
    lines: list[str] = []
    lines.append(f"subsystem={device.subsystem} {device.action=} {device.sys_path=}")
    lines.append(
        f"  usb_location (parsed sys_path)={UdevFilter.parse_usb_location(device.sys_path)}"
    )

    lines.append(f"  {device.device_node=}")
    lines.append(f"  {device.device_type=}")
    if device.action == "add" and device.device_type == "disk":
        if subsystem_filtered == "block":
            # We only log the mount point if we also filtered for "block".
            # For example the pico would not get here, as we filter for "tty"
            mount_point = UdevFilter.get_mount_point(
                device.device_node, allow_partition_mount=True
            )
            lines.append(f"  mount_point={mount_point}")

    def get_value(tag: str) -> str:
        value = device.properties.get(tag, None)
        if value is None:
            return "-"
        value_int = int(value, 16)
        return f"0x{value_int:04X}({value_int})"

    tags = ("ID_USB_VENDOR_ID", "ID_USB_MODEL_ID")
    tags_text = "/".join(tags)
    values_text = "/".join([get_value(tag) for tag in tags])
    lines.append(f"  device.properties['{tags_text}']={values_text}")
    return "\n".join(lines)


@dataclasses.dataclass
class UdevFilter:
    label: str
    usb_location: str
    udev_event_class: type[UdevEventBase]
    """
    Use Generics to propagate the return type of UdevPoller.expect_event()
    """
    id_vendor: int | None
    id_product: int | None
    subsystem: str
    device_type: None | str
    actions: list[str]

    @property
    def id_vendor_str(self) -> str:
        return f"{self.id_vendor:04x}"

    @property
    def id_product_str(self) -> str:
        return f"{self.id_product:04x}"

    @staticmethod
    def parse_usb_location(sys_path: str) -> str:
        match = _RE_USB_LOCATION.match(sys_path)
        assert match is not None, sys_path
        # Example 'match': '3-5.2.3'
        usb_location = match.group("location")
        assert usb_location != "0000"
        return usb_location

    @staticmethod
    def get_mount_point(device_node: str, allow_partition_mount: bool = False) -> str:
        """
        Example 'device_node': /dev/sda
        If 'allow_partition_mount': /dev/sda1 will be considered as allowed.
        """
        begin_s = time.monotonic()
        while time.monotonic() < begin_s + _TIMEOUT_MOUNT_S:
            for line in pathlib.Path("/proc/mounts").read_text().splitlines():
                partition, mount_point, _ = line.split(" ", maxsplit=2)
                if allow_partition_mount:
                    if partition.startswith(device_node):
                        return mount_point
                if partition == device_node:
                    return mount_point
            time.sleep(0.1)

        raise UdevTimoutException(f"Waiting for '{device_node}' to be mounted.")

    def matches(self, device: pyudev.Device) -> bool:
        if device.action not in self.actions:
            return False
        if device.subsystem != self.subsystem:
            return False
        usb_location = self.parse_usb_location(sys_path=device.sys_path)
        if usb_location != self.usb_location:
            return False

        try:
            id_vendor = device.properties["ID_USB_VENDOR_ID"]
            id_product = device.properties["ID_USB_MODEL_ID"]
        except KeyError:
            return False
        if self.id_vendor is not None:
            if id_vendor != self.id_vendor_str:
                return False
        if self.id_product is not None:
            if id_product != self.id_product_str:
                return False
        if device.device_type != self.device_type:
            return False
        return True


class Guard:
    """
    Make sure we flush the puller befor the stimuli which will create a event.
    This is to avoid race or out of sync conditions.
    """

    def __init__(self, udev_poller: UdevPoller):
        self._udev_poller = udev_poller

    def __enter__(self) -> UdevPoller:
        return self._udev_poller

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


class UdevPoller:
    def __init__(self) -> None:
        self.context = pyudev.Context()
        self.context.log_priority = syslog.LOG_NOTICE

        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.start()
        self.monitor.filter_by(subsystem="tty")
        self.monitor.filter_by(subsystem="usb", device_type="usb_device")
        self.monitor.filter_by(subsystem="block", device_type="disk")
        self.epoll = select.epoll()
        self.epoll.register(self.monitor.fileno(), select.POLLIN)

    def __enter__(self) -> Self:
        return self

    # mypy: allow-untyped-def
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def flush_events(self) -> None:
        flushed_events = self.epoll.poll(timeout=0.001)
        flushed_events_count = len(flushed_events)
        if flushed_events_count > 0:
            logger.debug(f"{flushed_events_count} events flushed")

    @property
    def guard(self) -> Guard:
        self.flush_events()
        return Guard(self)

    def expect_event(
        self,
        udev_filter: UdevFilter,
        text_where: str,
        text_expect: str,
        timeout_s: float = 1.0,
    ) -> UdevEventBase:
        while True:
            for _udev_filter_matched, event in self._do_poll(
                udev_filters=[udev_filter],
                text_where=text_where,
                text_expect=text_expect,
                timeout_s=timeout_s,
            ):
                return event

    def _do_poll(
        self,
        udev_filters: list[UdevFilter],
        text_where: str,
        text_expect: str,
        fail_filters: None | list[UdevFilter] = None,
        timeout_s: float = 1.0,
    ) -> Iterator[tuple[UdevFilter, UdevEventBase]]:
        assert isinstance(udev_filters, list)
        assert isinstance(fail_filters, None | list)
        assert isinstance(timeout_s, float)
        for f in udev_filters:
            assert isinstance(f, UdevFilter)
        if fail_filters is not None:
            for f in fail_filters:
                assert isinstance(f, UdevFilter)

        begin_s = time.monotonic()
        while True:
            duration_s = time.monotonic() - begin_s
            if duration_s > timeout_s:
                raise UdevTimoutException(
                    f"{text_where}: {text_expect}: duration_s {duration_s:0.3f}s of {timeout_s:0.3f}s."
                )
            events = self.epoll.poll(timeout=0.5)
            if len(events) == 0:
                logger.debug(f"Timeout {duration_s:0.2f}s of {timeout_s:0.2f}s")
                continue

            for fileno, _ in events:
                if fileno != self.monitor.fileno():
                    continue
                # TODO: rename 'device' -> 'device_event'
                # TODO: See also udev_event_class() below
                device = self.monitor.poll()
                for udev_filter in udev_filters:
                    if udev_filter.matches(device=device):
                        logger.debug(
                            f"matched:\n{get_device_debug(device=device, subsystem_filtered=udev_filter.subsystem)}"
                        )
                        yield udev_filter, udev_filter.udev_event_class(device=device)
                        continue
                    logger.debug(
                        f"not matched:\n{get_device_debug(device=device, subsystem_filtered=udev_filter.subsystem)}"
                    )

                if fail_filters is None:
                    continue

                for udev_filter in fail_filters:
                    if udev_filter.matches(device=device):
                        raise UdevFailException(
                            f"Event '{device}' matches '{udev_filter.label}'!"
                        )

    def close(self) -> None:
        self.epoll.close()


class UdevPollerLazy:
    def __init__(self) -> None:
        self._udev_poller: UdevPoller | None = None

    @property
    def udev_poller(self) -> UdevPoller:
        if self._udev_poller is None:
            self._udev_poller = UdevPoller()
        return self._udev_poller

    def close(self) -> None:
        if self._udev_poller is None:
            return
        self._udev_poller.close()
        self._udev_poller = None

    def __enter__(self) -> UdevPollerLazy:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


UDEV_POLLER_LAZY = UdevPollerLazy()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
