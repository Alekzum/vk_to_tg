from __future__ import annotations

import inspect
import pathlib
import sqlite3
import dotenv
import os
from functools import wraps
from dataclasses import dataclass
from typing import Any, Literal, TypeVar, overload
from utils.my_logging import getLogger
from .interface.user_settings import DB_PATH, UserSettingsManager

dotenv.load_dotenv(".env")
CHATS_BLACKLIST: list[str] = ['🚖🚕Такси "Ладья"🚕🚖']
config_path = pathlib.Path("data", "config.json")


logger = getLogger(__name__)
T = TypeVar("T")
_DEFAULT = object()
OWNER_ID = int(
    os.environ.get("OWNER_ID")
    or dotenv.set_key(
        ".env",
        "OWNER_ID",
        input("Введите ваш ID в телеграм (https://t.me/my_id_bot в помощь): "),
    )[2]
)


ENTRIES = ("_BOT_TOKEN",)
ENTIRES4FUNCS = Literal["BOT_TOKEN",]

UNSET = object()


def wrap_loaded_checker(self: "Config"):
    def check():
        if not self._is_loaded:
            raise RuntimeError(
                f"Need to {type(self).__name__}.load_values() before using this function!"
            )

    def check_for_loaded(func):
        def inner_sync(*args, **kwargs):
            check()
            return func(*args, **kwargs)

        async def inner_async(*args, **kwargs):
            check()
            return await func(*args, **kwargs)

        inner = inner_async if inspect.iscoroutinefunction(func) else inner_sync
        return wraps(func)(inner)

    return check_for_loaded


@dataclass
class Config:
    """If didn't found user with selected tg_id, it'll raise KeyError"""

    _BOT_TOKEN: str
    """For telegram bot"""

    chat_id: int

    _ACCESS_TOKEN: str
    """For vkontakte"""

    blacklist: set[str | int]
    """Which dialogs needs to be ignored"""

    _pts: int
    _ts: int

    pinned_message_id: int = -1
    """Message's id for "Unread chats count" updates """

    polling_state: bool = False

    max_msg_id: int = 0

    def __init__(self, tg_id: int):
        self._entries = ENTRIES
        self.dot_env_file = ".env"

        self._BOT_TOKEN = self.get_variable("BOT_TOKEN")
        self.chat_id = tg_id
        self._connector = sqlite3.connect(DB_PATH)

        self._is_loaded = False
        self.manager = UserSettingsManager(tg_id)
        # self.load_values()

    def __post_init__(self):
        loaded_wrapping = wrap_loaded_checker(self)
        self.save_variables = loaded_wrapping(self.save_variables)

    def set_pts(self, value: int):
        self._pts = value

    def set_ts(self, value: int):
        self._ts = value

    @property
    def pts(self):
        return self._pts

    @property
    def ts(self):
        return self._ts

    def __str__(self):
        return f"""<Config {self.chat_id=}"""

    def __repr__(self):
        return f"""utils.classes.Config({["{}={}".format(n, getattr(self, n)) for n in self._entries]})"""

    def __del__(self):
        self._connector.close()

    async def save_variables(self):
        await self.manager.user.set(
            blacklist=self.blacklist,
            pts=self.pts,
            ts=self.ts,
            pinned_message_id=self.pinned_message_id,
        )

    @classmethod
    async def load_user_values(cls, user_id: int):
        self = cls(user_id)
        return await self.load_values()

    async def load_values(self):
        user_info = await self.manager.user.get()
        self.polling_state = user_info.polling_state
        self.blacklist = user_info.blacklist
        self._ACCESS_TOKEN = user_info.vk_token
        self.pinned_message_id = user_info.pinned_message_id
        self.set_pts(user_info.pts)
        self.set_ts(user_info.ts)
        return self

    # @overload
    # def get_variable(self, variable_name: Literal["BOT_TOKEN"]) -> str: ...
    # @overload
    # def get_variable(self, variable_name: str) -> Any: ...

    # @overload
    # def get_variable(self, variable_name: Literal["ACCESS_TOKEN"]) -> str: ...
    # @overload
    # def get_variable(self, variable_name: Literal["NEED_UPDATE"]) -> bool: ...
    def get_variable(self: "Config", variable_name: ENTIRES4FUNCS):
        if not isinstance(variable_name, str) and isinstance(self, Config):
            raise TypeError(f"Variable name must be str, not {type(variable_name)}!")

        match variable_name:
            case "BOT_TOKEN":
                return os.environ.get("BOT_TOKEN") or self.update_variable("BOT_TOKEN")

            case _:
                raise KeyError('Need one of these values: "BOT_TOKEN"')

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

            case "all":
                for v in self._entries:
                    self.update_variable(v)

            case "max_msg_id":
                pass
