from typing import IO
import logging
import sys
import os
import copy


class MyFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="a", encoding=None, delay=False, errors=None):
        super().__init__(filename, mode, encoding, delay, errors)
        self.message_to_write = ""
        self.last_record = None
        self.counter = 0

    def _write(self, record, rewrite_line=False):
        if self.stream is None:
            if self.mode != "w" or not self._closed:
                self.stream = self._open()
        if self.stream:
            # MyStreamHandler.emit(self, record)
            self.emit_file(record, rewrite_line)

    def emit(self, record):
        if str(record) == str(self.last_record):
            self.counter += 1
            self.last_record = self.last_record or record
            temp_record = copy.deepcopy(self.last_record)
            temp_record.created = self.last_record.created
            temp_record.msg += f" x{self.counter}"
            self._write(temp_record, rewrite_line=True)
            return

        self._write(record, rewrite_line=False)
        self.last_record = record
        self.counter = 1

    def emit_file(self, record: logging.LogRecord, rewrite_line: bool = False):
        try:
            msg = self.format(record)
            stream = self.stream
            # issue 35046: merged two stream.writes into one.

            if self.message_to_write and not rewrite_line:
                stream.write(self.message_to_write)

            self.message_to_write = msg + "\n"
            # self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)

    def close(self):
        self.stream.write(self.message_to_write)
        with self.lock:
            try:
                if self.stream:
                    try:
                        self.flush()
                    finally:
                        stream = self.stream
                        self.stream = None
                        if hasattr(stream, "close"):
                            stream.close()
            finally:
                # Issue #19523: call unconditionally to
                # prevent a handler leak when delay is set
                # Also see Issue #42378: we also rely on
                # self._closed being set to True there
                MyStreamHandler.close(self)


class MyStreamHandler(logging.StreamHandler):
    def __init__(self, stream: IO | None = None):
        """
        Initialize the handler.

        If stream is not specified, sys.stderr is used.
        """
        logging.StreamHandler.__init__(self, stream)
        self.last_message: str = ""
        self.counter: int = 1
        self.last_record: logging.LogRecord | None = None

    def flush(self):
        """
        Flushes the stream.
        """
        with self.lock:
            if self.stream and hasattr(self.stream, "flush"):
                # self.stream.seek(-len(self.last_logged_message), os.SEEK_END)
                self.stream.flush()

    def _write(self, record: logging.LogRecord, rewrite_line: bool = False):
        try:
            msg = self.format(record)
            stream = self.stream
            # issue 35046: merged two stream.writes into one.
            stream.write("\r" + msg + ("" if rewrite_line else self.terminator))
            self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)

    def emit(self, record: logging.LogRecord):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """

        if str(record) == str(self.last_record):
            self.counter += 1
            self.last_record = self.last_record or record
            temp_record = copy.deepcopy(self.last_record)
            temp_record.created = self.last_record.created
            temp_record.msg += f" x{self.counter}"
            self._write(temp_record, rewrite_line=True)
            return

        self._write(record, rewrite_line=False)
        self.last_record = record
        self.counter = 1


# INFO WARN WARNING
formats = [
    "{asctime} - [{levelname}] {filename}:{funcName}:{lineno} {name} - {message}",
    "{asctime} - [{levelname}] {filename}:{funcName}:{lineno} {name} - {message}",
    "{asctime} - [{levelname}] {filename}:{lineno} {name} - {message}",
    "{asctime} - {levelname}:{lineno}\t {name} - {message}",
    "%(asctime)s - %(levelname)s (%(name)s) %(message)s",
]

FORMAT = formats[2]
LOG_FILE = "log.log"
LEVEL = logging.INFO
LEVEL_INFO = (
    logging.DEBUG if sys.argv[1:] and sys.argv[1] == "--debug" else logging.INFO
)
LEVEL_WARNING = (
    logging.DEBUG if sys.argv[1:] and sys.argv[1] == "--debug" else logging.WARNING
)

root_logger = logging.getLogger()
logger = logging.getLogger(__name__)

stream_handler = MyStreamHandler()
file_handler = MyFileHandler(LOG_FILE, encoding="utf-8")
temp_file_handler = MyFileHandler("temp" + LOG_FILE, mode="w", encoding="utf-8")

logging.basicConfig(
    format=FORMAT,
    level=LEVEL_INFO,
    handlers=[
        stream_handler,
        temp_file_handler,
        file_handler,
    ],
    style="{",
)

root_logger.setLevel(LEVEL_INFO)
stream_handler.setLevel(LEVEL_INFO)
file_handler.setLevel(LEVEL_INFO)
temp_file_handler.setLevel(LEVEL_INFO)

MUTE_DICT: dict[str, int | str] = {
    "httpcore": logging.WARNING,
    "urllib3": logging.WARNING,
    "asyncio": logging.INFO,
    "httpx": logging.WARNING,
    "utils": LEVEL_INFO,
    "bots": LEVEL_INFO,
}

for _name, _value in MUTE_DICT.items():
    _l = logging.getLogger(_name)
    _l.setLevel(_value)


if sys.argv[1:] and sys.argv[1] == "--debug":
    logger.debug(f"Starting via debug")
