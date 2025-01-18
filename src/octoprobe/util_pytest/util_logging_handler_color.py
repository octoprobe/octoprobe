import logging
import logging.config
import re
import typing

from rich.style import Style

logger = logging.getLogger(__file__)


# https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output/45394501
# https://github.com/Textualize/rich/blob/master/rich/color.py

_STYLE_FALLBACK = Style(color="purple")

_DICT_STYLES = {
    "COLOR_INFO": Style(color="blue"),
    "COLOR_SUCCESS": Style(color="green"),
    "COLOR_FAILED": Style(color="orange1"),
    "COLOR_ERROR": Style(color="red"),
}


class ColorHandler(logging.StreamHandler):
    RE_TAG = re.compile(r"^\[(?P<tag>COLOR_[A-Z]+)\](?P<msg>.*$)")
    """
    Example: [COLOR_INFO]This is a message
    tag: COLOR_INFO
    msg: This is a message
    """

    # FORMATTER = logging.Formatter("%(levelname)-8s - %(message)s")
    FORMATTER = logging.Formatter("%(message)s")

    @typing.override
    def format(self, record: logging.LogRecord) -> str:
        match = self.RE_TAG.match(record.msg)
        if match is None:
            return super().format(record)
        tag = match.group("tag")
        msg = match.group("msg")
        record.msg = msg
        color = _DICT_STYLES.get(tag, _STYLE_FALLBACK)

        if self.stream.isatty():
            message = self.FORMATTER.format(record)
            return color.render(message)

        return super().format(record)
