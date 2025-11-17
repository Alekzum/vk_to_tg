import logging
import logging.handlers
import os
import sys
import typing

import structlog

LOG_DIR = "logs"
LOG_FILE = "log.log"

IS_DEBUG = bool(sys.argv[1:] and "--debug" in sys.argv[1:])
IS_LOUD = bool(sys.argv[1:] and "--loud" in sys.argv[1:])

LEVEL = logging.INFO

LEVEL_INFO = logging.DEBUG if IS_DEBUG else logging.INFO
LEVEL_WARNING = logging.DEBUG if IS_DEBUG else logging.WARNING

STREAM_LEVEL = LEVEL_INFO
FILE_LEVEL = LEVEL_WARNING
TEMPFILE_LEVEL = LEVEL_INFO

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)


# TODO: show caller's caller modline instead caller's modline
# (add param depth?)
def my_callsite_processor(
    inclide_filename=True, include_funcname=True, inclide_lineno=True
):
    def inner(logger, method_name, event_dict):
        file_n, func_n, line_n = (
            event_dict.pop("filename", ""),
            event_dict.pop("func_name", ""),
            event_dict.pop("lineno", ""),
        )
        array = []
        if inclide_filename:
            array.append(file_n)
        if include_funcname:
            array.append(func_n)
        if inclide_lineno:
            array.append(line_n)
        args = tuple(array)
        event_dict["modline"] = ":".join(str(i) for i in args)
        return event_dict

    return inner


def filter_my_callsite_processor(blacklist: typing.Iterable = ()):
    def inner(logger, method_name, event):
        if any(logger.name.startswith(x) for x in blacklist):
            event.pop("modline")
        return event

    return inner


getLogger = structlog.stdlib.get_logger
get_logger = getLogger


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        my_callsite_processor(include_funcname=False),
        filter_my_callsite_processor(["aiogram", "pyrogram", "__main__"]),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

stream_formatter = structlog.stdlib.ProcessorFormatter(
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(),
    ],
)

file_formatter = structlog.stdlib.ProcessorFormatter(
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.processors.JSONRenderer(),
    ],
)

stream_handler = logging.StreamHandler()
file_handler = logging.handlers.TimedRotatingFileHandler(
    LOG_DIR + os.sep + LOG_FILE, encoding="utf-8", when="w0"
)
tempfile_handler = logging.FileHandler(
    LOG_DIR + os.sep + "temp" + LOG_FILE, encoding="utf-8", mode="w"
)

stream_handler.setFormatter(stream_formatter)
file_handler.setFormatter(file_formatter)
tempfile_handler.setFormatter(file_formatter)

stream_handler.setLevel(STREAM_LEVEL)
file_handler.setLevel(FILE_LEVEL)
tempfile_handler.setLevel(TEMPFILE_LEVEL)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)
root_logger.addHandler(tempfile_handler)
root_logger = structlog.wrap_logger(root_logger)

logger = structlog.get_logger(__name__)

logger.debug("Started", custom_level=LEVEL)
logger.info("Started", custom_level=LEVEL)


MUTE_DICT: dict[str, int | str] = {
    "aiosqlite": logging.INFO,
    "pyrogram": logging.ERROR,
    "pyrogram.crypto": logging.WARNING,
    "urllib3": LEVEL_WARNING,
    "asyncio": LEVEL_WARNING,
    "aiogram_dialog": LEVEL_INFO,
    "httpcore": LEVEL_WARNING,
    "httpx": LEVEL_WARNING,
    "utils": LEVEL_INFO,
    "bots": LEVEL_INFO,
}

for name, level in MUTE_DICT.items():
    logging.getLogger(name).setLevel(level)
