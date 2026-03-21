"""
https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output/45394501
https://github.com/Textualize/rich/blob/master/rich/color.py
https://rich.readthedocs.io/en/latest/appendix/colors.html#standard-colors
"""

import enum
import logging
import re
import typing

from rich.style import Style

logger = logging.getLogger(__file__)


_STYLE_FALLBACK = Style(color="purple")


class EnumColors(enum.Enum):
    _value_: Style
    COLOR_INFO = Style(color="white")
    COLOR_SUCCESS = Style(color="green")
    COLOR_FAILED = Style(color="orange1")
    COLOR_ERROR = Style(color="red")
    COLOR_SKIPPED = Style(color="light_slate_gray")
    COLOR_MP_REMOTE = Style(color="turquoise2")
    COLOR_TEST_STATEMENT = Style(color="bright_yellow")

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
    RE_TAG = re.compile(r"^\[(?P<tag>COLOR_[A-Z_]+)\](?P<msg>.*$)")
    """
    Example: [COLOR_INFO]This is a message
    tag: COLOR_INFO
    msg: This is a message
    """

    @typing.override
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        def render(style: Style) -> str:
            color = style + Style(
                italic=record.levelno < logging.INFO,
                dim=record.levelno < logging.INFO,
                bold=record.levelno > logging.INFO,
                blink=record.levelno > logging.ERROR,
            )
            return color.render(message)

        if not isinstance(record.msg, str):
            # 'record.msg' may be an exception...
            return render(style=EnumColors.COLOR_INFO.value)

        match = self.RE_TAG.match(record.msg)
        if match is None:
            return render(style=EnumColors.COLOR_INFO.value)

        # if not self.stream.isatty():
        #     return super().format(record)

        tag = match.group("tag")
        msg = match.group("msg")
        msg_before = record.msg
        try:
            record.msg = msg

            style = EnumColors.get_style(tag)
            return render(style=style)
        finally:
            record.msg = msg_before
