from typing import Iterable, MutableMapping
import structlog
import logging.handlers
import logging
import sys
import os

import dotenv


getLogger = get_logger = structlog.stdlib.get_logger

LOG_DIR = "logs"
LOG_FILE = "log.log"


IS_DEBUG = bool(
    sys.argv[1:]
    and "--debug" in sys.argv[1:]
    or dotenv.get_key(".env", "IS_DEBUG")
)
IS_LOUD = bool(
    sys.argv[1:]
    and "--loud" in sys.argv[1:]
    or dotenv.get_key(".env", "IS_LOUD")
)

LEVEL_INFO = logging.DEBUG if IS_DEBUG else logging.INFO
LEVEL_WARNING = logging.DEBUG if IS_DEBUG else logging.WARNING

LEVEL = LEVEL_INFO

LOUD_INFO = logging.DEBUG if IS_LOUD else logging.INFO
LOUD_WARNING = logging.DEBUG if IS_LOUD else logging.WARNING

STREAM_LEVEL = LEVEL
FILE_LEVEL = logging.WARNING
TEMPFILE_LEVEL = logging.DEBUG

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)


BASE_PATH = os.path.abspath(".")


def my_callsite_processor(
    include_filename=True,
    include_funcname=True,
    inclide_lineno=True,
    use_path_not_filename=True,
):
    def inner(logger, method_name: str, event_dict: MutableMapping):
        file_p: str = event_dict.pop("pathname", "")
        file_n: str = event_dict.pop("filename", "")
        func_n: str = event_dict.pop("func_name", "")
        line_n: int = event_dict.pop("lineno", "")

        array = []
        if include_filename and use_path_not_filename:
            array.append(file_p.removeprefix(BASE_PATH + os.sep))
        elif include_filename:
            array.append(file_n)
        if include_funcname:
            array.append(func_n)
        if inclide_lineno:
            array.append(line_n)
        args = tuple(array)
        event_dict["modline"] = "|" + ":".join(str(i) for i in args)
        return event_dict

    return inner


def remove_from_callsite_processor(blacklist: Iterable = ()):
    def inner(logger, method_name, event):
        if any(logger.name.startswith(x) for x in blacklist):
            event.pop("modline")
        return event

    return inner


structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ],
        ),
        my_callsite_processor(include_funcname=False),
        remove_from_callsite_processor(
            [
                "aiogram",
                "pyrogram",
                "__main__",
                "utils.my_patches",
            ]
        ),
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

logger.info("Logging module loaded", custom_level=LEVEL)

MUTEDICT = {
    "utils": logging.DEBUG,
    "httpx": LOUD_WARNING,
    "handlers": LEVEL_WARNING,
    "asyncio": LOUD_WARNING,
    "aiosqlite": logging.INFO,
    "httpcore": LOUD_WARNING,
    "html": logging.DEBUG,
    "pyrogram": logging.ERROR,
    "pyrogram.session": logging.WARNING,
    "pyrogram.crypto": logging.WARNING,
    "pyrogram.connection": logging.WARNING,
    "pyrogram.dispatcher": logging.WARNING,
    "utils.my_patches": LOUD_INFO,
    "utils.my_decorators": LOUD_INFO,
    "utils.config.my_types": LOUD_INFO,
    "utils.config.my_things": LOUD_INFO,
    "urllib3": LOUD_WARNING,
    "bots": logging.DEBUG,
    "bots.vk_bot.my_async_functions": LOUD_INFO,
    "bots.vk_bot.utils": LOUD_INFO,
}

for name, level in MUTEDICT.items():
    logging.getLogger(name).setLevel(level)
