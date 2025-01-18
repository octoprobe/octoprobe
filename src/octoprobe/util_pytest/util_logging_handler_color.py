import logging
import logging.config
import re
import typing

from rich.style import Style

logger = logging.getLogger(__file__)


# https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output/45394501
# https://github.com/Textualize/rich/blob/master/rich/color.py
def _get_style(color: str) -> Style:
    return Style(color=color)


# COLOR_INFO = "gray50"
# COLOR_SUCCESS = "green"
# COLOR_FAIL = "orange1"
# COLOR_ERROR = "red"

# _DICT_STYLES = {
#     tag: _get_style(color)
#     for tag, color in inspect.getmembers(util_colors)
#     if tag.startswith("COLOR_")
# }

# _STYLE_FALLBACK = Style(color="purple")

_STYLE_FALLBACK = Style(color="purple")

_DICT_STYLES = {
    "COLOR_INFO": Style(color="gray50"),
    "COLOR_SUCCESS": Style(color="green"),
    "COLOR_FAIL": Style(color="orange1"),
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

        message = self.FORMATTER.format(record)
        if self.stream.isatty():
            message = f"{color.render(message)}"
        return message
