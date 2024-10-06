from dataclasses import dataclass
from typing import Literal, Any, TypeVar
import logging
import json
import time
import os

import dotenv
import json
import re

from utils.runtime_platform import start_venv, in_venv


CHATS_BLACKLIST: list[str] = [
    '🚖🚕Такси "Ладья"🚕🚖'
]
configName: str = "config.json"
configPath: list[str] = ["data", configName]


logger = logging.getLogger(__name__)
T = TypeVar("T")
_DEFAULT = object()


try:
    import dpath
except ImportError:
    if not in_venv():
        start_venv()
    else:
        raise


@dataclass
class MyConfig:
    bot_token: str
    """For telegram bot"""

    chat_id: int
    """Chat id, where telegram bot will send messages (deprecated?)"""

    access_token: str
    """For vkontakte"""

    need_update: bool
    """Do program needs to be updated or not"""

    dot_env_file: str = ".env"
    """File with "secret" variables (aka .env file)"""
    
    def __init__(self):
        self._entries = ["bot_token", "chat_id", "access_token", "need_update"]
        self.dot_env_file = ".env"
        
        self.bot_token = dotenv.get_key(self.dot_env_file, "bot_token") or self.update_variable("bot_token")
        self.chat_id = int(dotenv.get_key(self.dot_env_file, "chat_id") or self.update_variable("chat_id"))
        self.access_token = dotenv.get_key(self.dot_env_file, "access_token") or self.update_variable("access_token")
        self.need_update = (_t:=dotenv.get_key(self.dot_env_file, "need_update")) and bool(int(_t)) or self.update_variable("need_update")

    def __str__(self):
        return f"""<Config {self.chat_id=}"""

    def __repr__(self):
        return f'''utils.classes.Config({['{}={}'.format(n, getattr(self, n)) for n in self._entries]})'''
    
    def update_variable(self, variable_name: str | Literal["bot_token", "chat_id", "access_token", "need_update", "all"]):
        dot_env_file = self.dot_env_file
        match variable_name:            
            case "bot_token":
                self.bot_token = input("Введите токен своего бота (может быть найден у https://t.me/botfather): ")
                dotenv.set_key(dot_env_file, "bot_token", self.bot_token)
                return self.bot_token

            case "chat_id":
                chat_id = ""
                while not chat_id.isdecimal():
                    chat_id = input("Введите ваш id в телеграм (https://t.me/my_id_bot в помощь): ")
                self.chat_id = int(chat_id)
                dotenv.set_key(dot_env_file, "chat_id", str(self.chat_id))
                return self.chat_id

            case "access_token":
                access_token = input("Введите ссылку из адресной строки по ссылке https://vk.cc/a6dCgm: ")
                self.access_token = (_re_find_token.findall(access_token) if not access_token.startswith("vk1.") else [access_token])[0]
                dotenv.set_key(dot_env_file, "access_token", self.access_token)
                return self.access_token
            
            case "need_update":
                need_update = ""
                while need_update.lower() not in ["y", "n"]:
                    need_update = input("Хотите получать обновления автоматически? (y/n): ").lower()
                self.need_update = True if need_update == "y" else False
                dotenv.set_key(dot_env_file, "need_update", str((int(self.need_update))))
                return self.need_update

            case "all":
                [self.update_variable(v) for v in self._entries]
    
    def set(self, path: list[str] | str, value: Any) -> bool | None:
        """Returns None if path didn't found, else return True"""
        if isinstance(path, str):
            path = [path]
        result = set_variable(path, value)
        return result

    def get(self, path: list[str] | str, default: Any = None) -> Any | None:
        """Works like dict.get"""
        if isinstance(path, str):
            path = [path]
        result = get_variable(path, default=default)
        return result

    def delete(self, path: list[str] | str) -> bool | None:
        """Works like dict.get"""
        if isinstance(path, str):
            path = [path]
        result = delete_variable(path)
        return result



pathPairs = list(zip(configPath, [None, *configPath[:-1]]))
"""pairs(child, parent)"""
_re_find_token = re.compile(r"access_token=([^&]+)")
configIsHere = all([childObject in os.listdir(parentObject) for (childObject, parentObject) in pathPairs])
# configIsHere = "config.json" in os.listdir("data")
configPathStr = os.sep.join(configPath)
_fileBusy = False
_updatetime = 0.01

_DEFAULT_RAW = dict(ts=None, pts=None)

Config = MyConfig()


def _wait_unlock():
    global _fileBusy
    while _fileBusy:
        time.sleep(_updatetime)


def _lock_file():
    global _fileBusy
    _fileBusy = True


def _unlock_file():
    global _fileBusy
    _fileBusy = False


def WithLocking(func):
    def inner(*args, **kwargs):
        _wait_unlock()
        _lock_file()
        result = func(*args, **kwargs)
        _unlock_file()
        return result
    return inner


# file things
def _get_date_dir(day_offset: int = 0) -> str:
    raw = time.time()
    t = time.localtime(raw + day_offset*86400)
    formating = "{:0>4}/{:0>2}/{:0>2}"
    result = formating.format(t.tm_year, t.tm_mon, t.tm_mday).replace("/", os.sep)
    return result


@WithLocking
def __load_raw() -> str:
    if not configIsHere:
        fake_raw = _DEFAULT_RAW
        fake_raw_file = json.dumps(fake_raw)
        with open(configPathStr, "w", encoding='utf-8') as file:
            file.write(fake_raw_file)
        return fake_raw_file

    with open(configPathStr, encoding='utf-8') as file:
        raw_file = file.read()
    return raw_file


def _load_raw(_fixed=False) -> dict:
    raw_file = __load_raw()
    raw = json.loads(raw_file)
    return raw


@WithLocking
def __save_raw(raw: dict) -> None:
    with open(configPathStr, 'w', encoding='utf-8') as file:
        json.dump(raw, file, indent=4, sort_keys=True, ensure_ascii=False)


def _save_raw(raw: dict):
    old_config = __load_raw()
    __save_raw(raw)
    return


# High level things


def get_variable(path: str | list[str], default: T | object = _DEFAULT) -> Any | T:
    raw = _load_raw()
    try:
        if default is _DEFAULT:
            value = dpath.get(raw, path)
        else:
            value = dpath.get(raw, path, default=default)
    except KeyError as ex:
        logger.warning(repr(ex))
        return None
    return value


def set_variable(path: list[str], value: Any) -> bool | None:
    raw = _load_raw()

    try:
        dpath.set(raw, path, value)

    except dpath.PathNotFound:
        return None

    _save_raw(raw)
    return True


def delete_variable(path: list[str]) -> bool | None:
    raw = _load_raw()

    try:
        dpath.delete(raw, path)

    except dpath.PathNotFound:
        return None

    _save_raw(raw)
    return True
