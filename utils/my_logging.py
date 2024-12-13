import logging


# INFO WARN WARNING
formats = [
    '{asctime} - [{levelname}] {filename}:{funcName}:{lineno} {name} - {message}',
    '{asctime} - [{levelname}] {filename}:{funcName}:{lineno} {name} - {message}',
    '{asctime} - [{levelname}] {filename}:{lineno} {name} - {message}',
    '{asctime} - {levelname}:{lineno}\t {name} - {message}',
    '%(asctime)s - %(levelname)s (%(name)s) %(message)s',
]

FORMAT = formats[2]
LOG_FILE = "log.log"
LEVEL = logging.INFO


customLogger = logging.Logger('customLogger')
rootLogger = logging.getLogger()

stream_handler = logging.StreamHandler()
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
logging.basicConfig(format=FORMAT, level=LEVEL, handlers=[stream_handler, file_handler], style="{")

logger = logging.getLogger(__name__)


MUTEDICT = {
    "httpx": logging.WARNING,
    "asyncio": logging.INFO,
}

for _name, _value in MUTEDICT.items():
    _l = logging.getLogger(_name)
    _l.setLevel(_value)