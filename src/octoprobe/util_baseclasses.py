from __future__ import annotations

import abc
import dataclasses
import enum
import pathlib  # pylint: disable=W0611:unused-import

from .util_tentacle_label.label_data import LabelData, LabelsData

TENTACLE_TYPE_MCU = "tentacle_mcu"


class OctoprobeTestException(Exception):
    """
    This exception terminates a test.
    """


class OctoprobeTestSkipException(OctoprobeTestException):
    """
    This exception terminates a test.
    """


class OctoprobeAppExitException(Exception):
    """
    This exception terminates the application

    When this exception is thrown, everything has been handled and logged.
    When this exception is caught, the only thing to do is the
    message "Terminating test due to OctoprobeTestException" and exit.
    """


class VersionMismatchException(OctoprobeTestException):
    def __init__(self, msg: str, version_installed: str, version_expected: str):
        assert isinstance(msg, str)
        assert isinstance(version_installed, str)
        assert isinstance(version_expected, str)
        self.msg = msg
        self.version_installed = version_installed
        self.version_expected = version_expected
        full_msg = f"{self.msg}: Version installed: '{self.version_installed}' but expected: '{self.version_expected}'!"
        super().__init__(full_msg)


def assert_micropython_repo(directory: pathlib.Path) -> None:
    if not (directory / "ports").is_dir():
        raise OctoprobeAppExitException(
            f"Directory does not point to the top of a micropython repo: {directory}"
        )


@dataclasses.dataclass
class UsbID:
    """
    The usb specification defines a vendor and a product id
    """

    vendor_id: int
    product_id: int

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(0x{self.vendor_id:04X}:0x{self.product_id:04X})"
        )


@dataclasses.dataclass
class BootApplicationUsbID:
    """
    A mcu typically has a different vendor-id/product-id in boot mode and application mode.
    """

    boot: UsbID
    """
    usb id's in boot/programming mode
    """
    application: UsbID
    """
    usb id's in application mode
    """


@dataclasses.dataclass(frozen=True)
class PropertyString:
    """
    Example: programmer=picotool,xy=5
    """

    text: str

    def get_tag_mandatory(self, tag: str) -> str:
        v = self.get_tag(tag=tag, mandatory=True)
        assert v is not None
        return v

    def get_tag(self, tag: str, mandatory: bool = False) -> None | str:
        """
        Example: get_tag("xy") -> "5"
        """
        if len(self.text) > 0:
            for x in self.text.split(","):
                _tag, value = x.split("=")
                if _tag == tag:
                    return value
        if mandatory:
            raise ValueError(f"No '{tag}' specified in '{self.text}'!")

        return None


@dataclasses.dataclass(frozen=True, repr=True, eq=True)
class TentacleSpecBase(abc.ABC):
    """
    Specification for a Tentacle, for example:

    >>> TentacleSpec(
        tentacle_type=TentacleType.TENTACLE_MCU,
        futs=[EnumFut.FUT_I2C, EnumFut.FUT_UART],
        label="pico",
        tags="boards=RPI_PICO,mcu=rp2,programmer=picotool",

    This class is heavely used in testcode and therefore has to support
    typehints and code completion to ease the work of writing/maintaining testcode.

    Therefore this class uses `generics
    <https://docs.python.org/3/library/typing.html#generics>`_.
    which allows to define parts of this class on testbed level.
    """

    tentacle_type: enum.StrEnum
    tentacle_tag: str
    futs: list[enum.StrEnum]
    doc: str
    tags: str
    relays_closed: dict[enum.StrEnum | None, list[int]] = dataclasses.field(
        default_factory=lambda: {None: []}
    )
    """
    If the key is None, the value defines the relays to be closed by default.
    """

    mcu_usb_id: BootApplicationUsbID | None = None
    programmer_args: list[str] = dataclasses.field(default_factory=list)
    """
    Special argumets...
    """

    def __post_init__(self) -> None:
        assert isinstance(self.tentacle_type, enum.StrEnum)
        assert isinstance(self.tentacle_tag, str)
        assert isinstance(self.futs, list)
        assert isinstance(self.doc, str)
        assert isinstance(self.tags, str)
        assert isinstance(self.relays_closed, dict)
        assert isinstance(self.mcu_usb_id, BootApplicationUsbID | None)
        assert isinstance(self.programmer_args, list)

    def __hash__(self) -> int:
        return hash(f"{self.tentacle_type}-{self.tentacle_tag}")

    def get_tag(self, tag: str) -> str | None:
        """
        Find a tag in a string like ``boards=RPI_PICO,mcu=rp2,programmer=picotool``.

        :param tag: ``mcu`` in above string
        :type tag: str
        :return: In this example: ``rp2``
        :rtype: str | None
        """
        return PropertyString(self.tags).get_tag(tag)

    def get_tag_mandatory(self, tag: str) -> str:
        return PropertyString(self.tags).get_tag_mandatory(tag)

    @property
    def is_mcu(self) -> bool:
        return self.tentacle_type.value == TENTACLE_TYPE_MCU

    @property
    @abc.abstractmethod
    def description(self) -> str: ...


@dataclasses.dataclass(frozen=True, repr=True, eq=True)
class TentacleInstance:
    serial: str
    tentacle_spec: TentacleSpecBase
    hw_version: str
    testbed_name: str
    testbed_instance: str

    @property
    def label_data(self) -> LabelData:
        return LabelData(
            serial=self.serial[-4:],
            description=self.tentacle_spec.description,
            tentacle_tag=self.tentacle_spec.tentacle_tag,
            tentacle_type=self.tentacle_spec.tentacle_type,
            testbed_name=self.testbed_name,
            testbed_instance=self.testbed_instance,
        )


class TentaclesInventory(dict[str, TentacleInstance]):
    @property
    def labels_data(self) -> LabelsData:
        return LabelsData([instance.label_data for instance in self.values()])


class TentaclesCollector:
    """
    Allows to create inventory lists in a compact form.
    """

    def __init__(self, testbed_name: str) -> None:
        assert isinstance(testbed_name, str)
        self.testbed_name = testbed_name
        self.inventory = TentaclesInventory()

    def set_testbed_name(self, testbed_name: str) -> TentaclesCollector:
        assert isinstance(testbed_name, str)
        self.testbed_name = testbed_name
        return self

    def add_testbed_instance(
        self, testbed_instance: str, tentacles: list[tuple[str, str, TentacleSpecBase]]
    ) -> TentaclesCollector:
        assert isinstance(testbed_instance, str)
        assert isinstance(tentacles, list)

        for serial, hw_version, tentacle_spec in tentacles:
            assert isinstance(serial, str)
            assert isinstance(hw_version, str)
            assert isinstance(tentacle_spec, TentacleSpecBase)
            tentacle_instance = TentacleInstance(
                serial=serial,
                hw_version=hw_version,
                tentacle_spec=tentacle_spec,
                testbed_name=self.testbed_name,
                testbed_instance=testbed_instance,
            )
            assert tentacle_instance.serial not in self.inventory, (
                f"Duplicated tentacle serial {tentacle_instance.serial}!"
            )
            self.inventory[tentacle_instance.serial] = tentacle_instance

        return self
