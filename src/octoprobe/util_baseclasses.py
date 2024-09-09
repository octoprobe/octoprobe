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


@dataclasses.dataclass
class TentacleSpec[TMcuConfig, TTentacleType: enum.StrEnum, TEnumFut: enum.StrEnum]:
    tentacle_type: TTentacleType
    futs: list[TEnumFut]
    category: str
    label: str
    doc: str
    tags: str
    relays_closed: dict[TEnumFut, list[int]]
    mcu_config: TMcuConfig | None = None
    mcu_usb_id: BootApplicationUsbID | None = None

    def get_tag(self, tag: str) -> str | None:
        return PropertyString(self.tags).get_tag(tag)

    def get_tag_mandatory(self, tag: str) -> str:
        return PropertyString(self.tags).get_tag_mandatory(tag)

    @property
    def is_mcu(self) -> bool:
        return self.mcu_config is not None
