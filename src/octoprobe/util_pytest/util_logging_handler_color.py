import enum
import logging
import re
import typing

from rich.style import Style

logger = logging.getLogger(__file__)


# https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output/45394501
# https://github.com/Textualize/rich/blob/master/rich/color.py

_STYLE_FALLBACK = Style(color="purple")


class EnumColors(enum.Enum):
    _value_: Style
    COLOR_INFO = Style(color="blue")
    COLOR_SUCCESS = Style(color="green")
    COLOR_FAILED = Style(color="orange1")
    COLOR_ERROR = Style(color="red")
    COLOR_SKIPPED = Style(color="light_slate_gray")

    @property
    def with_brackets(self) -> str:
        """
        Example: [COLOR_INFO]
        """
        return f"[{self.name}]"

    @classmethod
    def get_style(cls, color: str) -> Style:
        try:
            return cls[color].value
        except KeyError:
            return _STYLE_FALLBACK


class ColorFormatter(logging.Formatter):
    RE_TAG = re.compile(r"^\[(?P<tag>COLOR_[A-Z]+)\](?P<msg>.*$)")
    """
    Example: [COLOR_INFO]This is a message
    tag: COLOR_INFO
    msg: This is a message
    """

    @typing.override
    def format(self, record: logging.LogRecord) -> str:
        if not isinstance(record.msg, str):
            # 'record.msg' may be an exception...
            return super().format(record)

        match = self.RE_TAG.match(record.msg)
        if match is None:
            return super().format(record)
        # if not self.stream.isatty():
        #     return super().format(record)

        tag = match.group("tag")
        msg = match.group("msg")
        msg_before = record.msg
        try:
            record.msg = msg
            color = EnumColors.get_style(tag)

            message = super().format(record)
            return color.render(message)
        finally:
            record.msg = msg_before
