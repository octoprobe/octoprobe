import re

SERIALNUMBER_LONG = 16
"""
Example: e46340474b551722
"""
SERIALNUMBER_DELIMITED = SERIALNUMBER_LONG + 1
"""
Example: e46340474b55-1722
"""
SERIALNUMBER_SHORT = 4
"""
Example: 2731
"""
SERIALNUMBER_DELIMITER = "-"
"""
Example: e46340474b4c-2731
"""
REGEX_SERIAL_DELIMITED = re.compile(r"^\w{12}-\w{4}$")
REGEX_SERIAL = re.compile(r"^\w{16}$")
"""
Example: e46340474b4c2731
"""


def get_serial_delimited(serial: str) -> str:
    """
    Example
    serial: e46340474b551722
    return: e46340474b55-1722
    """
    assert isinstance(serial, str)
    assert len(serial) == SERIALNUMBER_LONG, (
        f"Expect len {SERIALNUMBER_LONG} but got {len(serial)}: {serial}"
    )
    return (
        serial[:-SERIALNUMBER_SHORT]
        + SERIALNUMBER_DELIMITER
        + serial[-SERIALNUMBER_SHORT:]
    )


def serial_short_from_delimited(serial: str) -> str:
    """
    Example
    serial: e46340474b551722 or e46340474b55-1722
    return: 1722
    """
    assert isinstance(serial, str)
    assert len(serial) in (SERIALNUMBER_LONG, SERIALNUMBER_DELIMITED), (
        f"Expect len {SERIALNUMBER_LONG} or {SERIALNUMBER_LONG} but got {len(serial)}: {serial}"
    )
    return serial[-SERIALNUMBER_SHORT:]


def is_serial_valid(serial: str) -> bool:
    return REGEX_SERIAL.match(serial) is not None


def is_serialdelimtied_valid(serial_delimited: str) -> bool:
    return REGEX_SERIAL_DELIMITED.match(serial_delimited) is not None


def assert_serial_valid(serial: str) -> None:
    if not is_serial_valid(serial=serial):
        raise ValueError(
            f"Serial '{serial}' is not valid. Expected: {REGEX_SERIAL.pattern}"
        )


def assert_serialdelimted_valid(serial_delimited: str) -> None:
    if not is_serialdelimtied_valid(serial_delimited=serial_delimited):
        raise ValueError(
            f"Serial '{serial_delimited}' is not valid. Expected: {REGEX_SERIAL_DELIMITED.pattern}"
        )
