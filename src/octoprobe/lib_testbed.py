import dataclasses
import logging

from testbed.constants import TentacleType

from octoprobe.lib_tentacle import Tentacle

logger = logging.getLogger(__file__)


@dataclasses.dataclass
class Testbed:
    """
    A minimal testbed just contains tentacles.
    However, it might also include usb-hubs, wlan-accesspoints, etc.
    """

    workspace: str
    tentacles: list[Tentacle]

    def __post_init__(self) -> None:
        assert isinstance(self.tentacles, list)

    @property
    def description_short(self) -> str:
        return Tentacle.tentacles_description_short(tentacles=self.tentacles)

    def get_tentacle(
        self, tentacle_type: TentacleType | None = None, serial: str | None = None
    ) -> Tentacle:
        assert isinstance(tentacle_type, TentacleType | None)
        assert isinstance(serial, str | None)

        list_tentacles: list[Tentacle] = []
        for tentacle in self.tentacles:
            if tentacle_type is not None:
                if tentacle_type != tentacle.tentacle_spec.tentacle_type:
                    continue
            if serial is not None:
                if serial != tentacle.tentacle_serial_number:
                    continue
            list_tentacles.append(tentacle)

        line_criterial = f"Criteria tentacle_type='{tentacle_type}', serial='{serial}'."

        if len(list_tentacles) == 0:
            lines: list[str] = [
                "No tentacles found.",
                line_criterial,
                "These tenacles are configured:",
                self.description_short,
            ]
            raise ValueError("\n".join(lines))

        if len(list_tentacles) > 1:
            lines: list[str] = [
                f"{len(list_tentacles)} tentacles match. Please specify serial.",
                line_criterial,
                "These tenacles are configured and already selected:",
                Tentacle.tentacles_description_short(tentacles=list_tentacles),
            ]
            raise ValueError("\n".join(lines))

        return list_tentacles[0]
