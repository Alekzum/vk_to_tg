from collections import defaultdict
from typing import Any, Optional
import subprocess
import logging
import venv
import sys
import os


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


# class CooldownFilter(logging.Filter):
#     """Do not print same line if time after previous line less or equal <COOLDOWN> seconds. Defaults to 5 seconds"""
#     def __init__(self, cooldown=5, name=''):
#         """
#         Initialize a filter.

#         Initialize with the name of the logger which, together with its
#         children, will have its events allowed through the filter. If no
#         name is specified, allow every event.
#         """
#         # self.name = name
#         # self.nlen = len(name)
#         self.cooldown = cooldown
    
#     last_events: dict[str, float] = defaultdict(float)
    
#     def filter(self, record) -> bool:
#         prev_time = self.last_events[record.name]
#         if prev_time + self.cooldown <= record.created:
#             self.last_events[record.name] = record.created
#             return True
#         else:
#             return False


customLogger = logging.Logger('customLogger')
rootLogger = logging.getLogger()
# rootLogger.addFilter(CooldownFilter(10))

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
    # _l.addFilter(CooldownFilter())
    # _l.addFilter(CountFilter())