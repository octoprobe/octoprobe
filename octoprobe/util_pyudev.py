from __future__ import annotations

import abc
import dataclasses
import logging
import select
import syslog
import time
from collections.abc import Iterator
from typing import Any, Self

import pyudev  # type: ignore

logger = logging.getLogger(__file__)


class UdevFailEvent(Exception):
    pass


class UdevEventBase(abc.ABC):
    @abc.abstractmethod
    def __init__(self, device: pyudev.Device): ...


@dataclasses.dataclass
class UdevFilter:
    label: str
    udev_event_class: type[UdevEventBase]
    id_vendor: int
    id_product: int
    subsystem: str
    device_type: None | str
    actions: list[str]

    @property
    def id_vendor_str(self) -> str:
        return f"{self.id_vendor:04x}"

    @property
    def id_product_str(self) -> str:
        return f"{self.id_product:04x}"

    def matches(self, device: pyudev.Device) -> bool:
        if device.action not in self.actions:
            return False
        if device.subsystem != self.subsystem:
            return False
        try:
            id_vendor = device.properties["ID_USB_VENDOR_ID"]
            id_product = device.properties["ID_USB_MODEL_ID"]
        except KeyError:
            return False
        if id_vendor != self.id_vendor_str:
            return False
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
        self.monitor.filter_by(subsystem="usb")
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
            for event in self._do_poll(
                filters=[udev_filter],
                text_where=text_where,
                text_expect=text_expect,
                timeout_s=timeout_s,
            ):
                return event

    def _do_poll(
        self,
        filters: list[UdevFilter],
        text_where: str,
        text_expect: str,
        fail_filters: None | list[UdevFilter] = None,
        timeout_s: float = 1.0,
    ) -> Iterator[UdevEventBase]:
        assert isinstance(filters, list)
        assert isinstance(fail_filters, None | list)
        assert isinstance(timeout_s, float)
        for f in filters:
            assert isinstance(f, UdevFilter)
        if fail_filters is not None:
            for f in fail_filters:
                assert isinstance(f, UdevFilter)

        begin_s = time.monotonic()
        while True:
            duration_s = time.monotonic() - begin_s
            if duration_s > timeout_s:
                raise TimeoutError(
                    f"{text_where}: {text_expect}: duration_s {duration_s:0.3f}s of {timeout_s:0.3f}s."
                )
            events = self.epoll.poll(timeout=0.5)
            if len(events) == 0:
                logger.debug("Timeout")
                continue

            for fileno, _ in events:
                if fileno != self.monitor.fileno():
                    continue
                device = self.monitor.poll()
                for udev_filter in filters:
                    if udev_filter.matches(device=device):
                        yield udev_filter.udev_event_class(device=device)
                        continue

                if fail_filters is None:
                    continue
                    raise UdevFailEvent(f"Unexpected event '{device}'!")

                for udev_filter in fail_filters:
                    if udev_filter.matches(device=device):
                        raise UdevFailEvent(
                            f"Event '{device}' matches '{udev_filter.label}'!"
                        )

    def close(self) -> None:
        self.epoll.close()


def main() -> None:
    pass


if __name__ == "__main__":
    main()
