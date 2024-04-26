import logging
import time

from usbhubctl.util_logging import init_logging

logger = logging.getLogger(__file__)


def main() -> None:
    init_logging()

    start_s = time.monotonic()

    logger.info(f"duration {time.monotonic()-start_s:0.1f}s")


if __name__ == "__main__":
    main()
