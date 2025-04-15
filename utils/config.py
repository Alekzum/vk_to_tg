from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Any, TypeVar, overload
import logging
import json
import time

from dpath.exceptions import PathNotFound
import pathlib
import dotenv
import dpath
import re

from .interface.user_settings import DB_PATH, get_user, save_user
import sqlite3


CHATS_BLACKLIST: list[str] = ['🚖🚕Такси "Ладья"🚕🚖']
config_path = pathlib.Path("data", "config.json")


logger = logging.getLogger(__name__)
T = TypeVar("T")
_DEFAULT = object()
OWNER_ID = int(dotenv.get_key(".env", "CHAT_ID") or dotenv.set_key(".env", "CHAT_ID", input("Введите ваш ID в телеграм (https://t.me/my_id_bot в помощь): "))[2])


ENTRIES = (
    "_BOT_TOKEN",
    "ADMIN_IDS",
)
ENTIRES4FUNCS = Literal[
    "BOT_TOKEN",
    "ADMIN_IDS",
]

UNSET = object()


@dataclass
class Config:
    """If didn't found user with selected tg_id, it'll raise KeyError"""
    _BOT_TOKEN: str
    """For telegram bot"""

    _chat_id: int
    _ADMIN_IDS: list[int]
    """User ids, which can use dev commands"""

    _ACCESS_TOKEN: str
    """For vkontakte"""

    _blacklist: set[str]
    """Which dialogs needs to be ignored"""

    _pts: int
    _ts: int
    POLLING_STATE: bool = False

    max_msg_id: int = 0

    def __init__(self, chat_id: int):
        self._entries = ENTRIES
        self.dot_env_file = ".env"

        self._BOT_TOKEN = self.get_variable("BOT_TOKEN")
        self._ADMIN_IDS = self.get_variable("ADMIN_IDS")
        self._chat_id = chat_id
        self._connector = sqlite3.connect(DB_PATH)
        self.load_values()

    def __str__(self):
        return f"""<Config {self._ADMIN_IDS=}"""

    def __repr__(self):
        return f"""utils.classes.Config({['{}={}'.format(n, getattr(self, n)) for n in self._entries]})"""
    
    def __del__(self):
        self._connector.close()

    def save_values(self):
        save_user(self._chat_id, self._blacklist, self._pts, self._ts)
        ...

    def load_values(self):
        user_info = get_user(self._chat_id)
        self._blacklist = user_info.blacklist
        self._ACCESS_TOKEN = user_info.vk_token
        self.POLLING_STATE = user_info.pooling_state
        self._pts = user_info.pts
        self._ts = user_info.ts

    @overload
    def get_variable(self, variable_name: Literal["ADMIN_IDS"]) -> list[int]: ...
    @overload
    def get_variable(self, variable_name: Literal["BOT_TOKEN"]) -> str: ...

    # @overload
    # def get_variable(self, variable_name: Literal["ACCESS_TOKEN"]) -> str: ...
    # @overload
    # def get_variable(self, variable_name: Literal["NEED_UPDATE"]) -> bool: ...
    def get_variable(self: "Config", variable_name: ENTIRES4FUNCS):
        if not isinstance(variable_name, str) and isinstance(self, Config):
            raise TypeError(f"Variable name must be str, not {type(variable_name)}!")

        match variable_name:
            case "BOT_TOKEN":
                return dotenv.get_key(
                    self.dot_env_file, "BOT_TOKEN"
                ) or self.update_variable("BOT_TOKEN")

            case "ADMIN_IDS":
                if env_admin_ids := dotenv.get_key(self.dot_env_file, "ADMIN_IDS"):
                    return list(int(i.strip()) for i in env_admin_ids.split(","))

                return self.update_variable("ADMIN_IDS")

            case _:
                raise KeyError(
                    'Need one of these values: "BOT_TOKEN", "ADMIN_IDS"'
                )

    @overload
    def update_variable(self, variable_name: Literal["ADMIN_IDS"]) -> list[int]: ...
    @overload
    def update_variable(self, variable_name: Literal["BOT_TOKEN"]) -> str: ...

    @overload
    def update_variable(self, variable_name: Literal["all"]) -> None: ...
    @overload
    def update_variable(self, variable_name: str) -> Any: ...
    def update_variable(
        self,
        variable_name: (
            str
            | Literal[
                "BOT_TOKEN",
                "ADMIN_IDS",
                "all",
            ]
        ),
    ):
        dot_env_file = self.dot_env_file
        match variable_name:
            case "BOT_TOKEN":
                self._BOT_TOKEN = input(
                    "Введите токен своего бота (может быть найден у https://t.me/botfather): "
                )
                dotenv.set_key(dot_env_file, "BOT_TOKEN", self._BOT_TOKEN)
                return self._BOT_TOKEN

            case "ADMIN_IDS":
                ADMIN_IDS = ""
                while not all(i.strip().isdecimal() for i in ADMIN_IDS.split(",")):
                    ADMIN_IDS = input(
                        "Введите id пользователей-админов в телеграм (https://t.me/my_id_bot в помощь, писать через запятую): "
                    )
                self._ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS.split(",")]
                dotenv.set_key(dot_env_file, "ADMIN_IDS", str(self._ADMIN_IDS))
                return self._ADMIN_IDS

            case "all":
                for v in self._entries:
                    self.update_variable(v)

            case "max_msg_id":
                pass
