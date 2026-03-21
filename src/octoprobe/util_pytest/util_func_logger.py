import functools
import inspect
import logging
import pathlib

from octoprobe.util_pytest.util_logging_handler_color import EnumColors

logger = logging.getLogger(__file__)


def func_logger(func):
    """
    log this call
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        bound = inspect.signature(func).bind(*args, **kwargs)
        bound.apply_defaults()

        params = ", ".join(
            f"{k}={v!r}" for k, v in bound.arguments.items() if k != "self"
        )
        frame = inspect.stack()[1]
        caller = f"{pathlib.Path(frame.filename).name}:{frame.lineno}"
        func_text = f"{EnumColors.COLOR_TEST_STATEMENT.with_brackets}{caller} {func.__name__}({params})  "
        logger.info(func_text)
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.exception(msg=f"{func.__name__}({params})  [{caller}]", exc_info=e)
            raise

    return wrapper
