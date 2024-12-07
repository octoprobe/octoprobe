import dataclasses
import enum  # pylint: disable=W0611:unused-import


@dataclasses.dataclass
class UsbID:
    """
    The usb specification defines a vendor and a product id
    """

    vendor_id: int
    product_id: int


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
class TentacleSpec[TMcuConfig, TTentacleType: enum.StrEnum, TEnumFut: enum.StrEnum]:
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

    tentacle_type: TTentacleType
    tentacle_tag: enum.StrEnum
    futs: list[TEnumFut]
    doc: str
    tags: str
    relays_closed: dict[TEnumFut, list[int]] = dataclasses.field(default_factory=dict)
    mcu_config: TMcuConfig | None = None
    mcu_usb_id: BootApplicationUsbID | None = None
    programmer_args: list[str] = dataclasses.field(default_factory=list)
    micropython_perftest_args: list[str] | None = None
    """
    Special argumets...
    """

    def __post_init__(self) -> None:
        assert isinstance(self.tentacle_type, enum.StrEnum)
        assert isinstance(self.tentacle_tag, enum.StrEnum)
        assert isinstance(self.futs, list)
        assert isinstance(self.doc, str)
        assert isinstance(self.tags, str)
        assert isinstance(self.relays_closed, dict)
        assert isinstance(self.mcu_usb_id, BootApplicationUsbID | None)
        assert isinstance(self.programmer_args, list)
        assert isinstance(self.micropython_perftest_args, list | None)

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
        return self.mcu_config is not None
