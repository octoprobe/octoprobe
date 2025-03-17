import json
import logging
import logging.config
import pathlib
import time

from ..lib_tentacle_infra import TentacleInfra
from ..usb_tentacle.usb_tentacle import UsbTentacle, UsbTentacles
from ..util_firmware_spec import FirmwareDownloadSpec
from ..util_pyudev import UdevPoller

logger = logging.getLogger(__file__)

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).parent
FILENAME_LOGGING_JSON = DIRECTORY_OF_THIS_FILE / "commissioning_logging.json"
assert FILENAME_LOGGING_JSON.is_file()


def init_logging() -> None:
    logging.config.dictConfig(json.loads(FILENAME_LOGGING_JSON.read_text()))


def do_commissioning() -> None:
    """
    Listen for new tentacles (udev).
    Display connected tentacle.
    USB:
      * Toggle DUT Power
      * Toggle Error LED
      * Infra Boot: On
      * Infra Power: On
    RP2 Infra
      * Program RP2
      * Cycle Relays
      * Toggle DUT Boot
    """
    init_logging()

    firmware_spec = TentacleInfra.get_firmware_spec()
    firmware_spec.download()

    while True:
        c = Commissioning()
        try:
            with UdevPoller() as udev:
                c.do_program_rp2(udev=udev, firmware_spec=firmware_spec)
                while True:
                    c.do_commissioning()
        except Exception as e:
            logger.warning(e)
            time.sleep(1.0)


class MsgPeriod:
    def __init__(self) -> None:
        self._last_msg_s = 0.0

    @property
    def do_print(self) -> bool:
        duration_since_last_msg_s = time.monotonic() - self._last_msg_s
        if duration_since_last_msg_s > 10.0:
            self._last_msg_s = time.monotonic()
            return True
        return False


class Commissioning:
    def __init__(self) -> None:
        connected_tentacle = self._wait_for_connected_tentacle()
        self.tentacle_infra = TentacleInfra(
            "tentacle_to_commission",
            usb_tentacle=connected_tentacle,
        )
        logger.info(
            f"Tentacle detected at usb location: {connected_tentacle.hub4_location.short}"
        )
        time.sleep(1.0)

    def _wait_for_connected_tentacle(self) -> UsbTentacle:
        msg_period = MsgPeriod()

        while True:
            # actual_usb_topology = backend_query_lsusb.lsusb()
            usb_tentacles = UsbTentacles.query(poweron=False)

            if len(usb_tentacles) > 1:
                if msg_period.do_print:
                    logger.warning(
                        f"{len(usb_tentacles)} tentacles connected: Please connect exactly one tentacle!"
                    )
                time.sleep(0.5)
                continue
            if len(usb_tentacles) == 0:
                if msg_period.do_print:
                    logger.info(
                        f"{len(usb_tentacles)} tentacles connected: Please connect a tentacle!"
                    )
                time.sleep(0.5)
                continue
            return usb_tentacles[0]

    def do_program_rp2(
        self,
        udev: UdevPoller,
        firmware_spec: FirmwareDownloadSpec,
    ) -> None:
        assert isinstance(udev, UdevPoller)
        assert isinstance(firmware_spec, FirmwareDownloadSpec)

        self.tentacle_infra.flash(
            udev=udev,
            filename_firmware=firmware_spec.filename,
            directory_test=pathlib.Path("/tmp"),
            usb_location=self.tentacle_infra.usb_location_infra,
        )
        self.tentacle_infra.verify_micropython_version(firmware_spec=firmware_spec)

        mcu_infra = self.tentacle_infra.mcu_infra
        unique_id = mcu_infra.get_unique_id()
        logger.info(f"Flashed tentacle. Serial Number is '{unique_id}'.")
        logger.info(f"* Please write onto the tentacle: {unique_id[-4:]}")
        logger.info(
            "* Please verify that the LEDs flash: DUT Power, Error, Relay 1..n!"
        )
        logger.info("* Please check the relays impedance with a Ohm meter!")
        mcu_infra.exception_if_files_on_flash()

    def do_commissioning(self) -> None:
        self.tentacle_infra.power.error = True
        self.tentacle_infra.power.dut = True
        time.sleep(1.0)
        self.tentacle_infra.power.error = False
        self.tentacle_infra.power.dut = False
        time.sleep(1.0)

        mcu_infra = self.tentacle_infra.mcu_infra

        if False:
            # Running von 1 to 7
            for i0 in range(self.tentacle_infra.RELAY_COUNT):
                mcu_infra.active_led(on=bool(i0 % 2))

                mcu_infra.relays(relays_close=[i0 + 1])
                time.sleep(1.0)
                mcu_infra.relays(relays_open=[i0 + 1])

        if True:
            # Alternating
            even = [2, 4, 6]
            odd = [1, 3, 5, 7]
            mcu_infra.active_led(on=True)
            mcu_infra.relays(relays_close=even, relays_open=odd)
            time.sleep(1.0)
            mcu_infra.active_led(on=False)
            mcu_infra.relays(relays_close=odd, relays_open=even)
