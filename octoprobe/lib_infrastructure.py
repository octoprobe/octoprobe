import dataclasses
import io
import textwrap

from octoprobe.lib_tentacle import Tentacle


@dataclasses.dataclass
class Infrastructure:
    """
    A minimal infrastructure just contains tentacles.
    However, it might also include usb-hubs, wlan-accesspoints, etc.
    """

    workspace: str
    tentacles: list[Tentacle]

    def __post_init__(self) -> None:
        assert isinstance(self.tentacles, list)

    @property
    def description_short(self) -> str:
        f = io.StringIO()
        f.write("TENTACLES\n")
        for tentacle in self.tentacles:
            f.write(textwrap.indent(tentacle.description_short, prefix="  "))

        return f.getvalue()
