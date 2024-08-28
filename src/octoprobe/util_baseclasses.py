import dataclasses
import enum  # pylint: disable=W0611:unused-import


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

    def get_property(self, tag: str) -> str | None:
        return PropertyString(self.tags).get_tag(tag)

    def get_property_mandatory(self, tag: str) -> str:
        return PropertyString(self.tags).get_tag_mandatory(tag)
