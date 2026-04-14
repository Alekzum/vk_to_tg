from abc import ABC, abstractmethod

from pydantic import BaseModel, Field
from typing import Iterable, Any, overload, Literal
import aiosqlite
import asyncio

# import sqlite3
import pathlib
import gzip


class UserInfo(BaseModel):
    tg_id: int
    polling_state: bool = False
    vk_token: str = ""
    blacklist_: bytes = Field(b"", alias="blacklist")
    pts: int = 0
    ts: int = 0
    pinned_message_id: int = -1

    @property
    def blacklist(self) -> set[str | int]:
        return _drl_blacklist(self.blacklist_ or b"")


_DB_PATH = ["data", "database.db"]
TABLE_NAME = "UserInfo"

DB_PATH = str(pathlib.Path(*_DB_PATH))
_BLACKLIST_SEP = "\\•\\"
_UNSET = object()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
    tg_id INTEGER PRIMARY KEY,
    polling_state INTEGER,
    vk_token TEXT,
    blacklist BLOB,
    pts INTEGER,
    ts INTEGER
    )"""
        )
        await con.commit()


async def _init_user(tg_id: int, vk_token: str):
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""INSERT INTO {TABLE_NAME} (tg_id, polling_state, vk_token, blacklist) VALUES (?, 0, ?, ?)""",
            (tg_id, vk_token, b""),
        )
        await con.commit()


USER_KEYS = (
    "tg_id",
    "polling_state",
    "vk_token",
    "blacklist",
    "pts",
    "ts",
    "pinned_message_id",
)


def parse_user(raw) -> UserInfo:
    return UserInfo.model_validate({k: v for (k, v) in zip(USER_KEYS, raw)})


@overload
async def _get_user[T](tg_id: int, default: T) -> UserInfo | T: ...
@overload
async def _get_user(tg_id: int, default: Any = _UNSET) -> UserInfo: ...
async def _get_user[T](tg_id: int, default: T | Any = _UNSET) -> UserInfo | T:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(f"""SELECT * FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,))
        raw = await cur.fetchone()  # : tuple | None

    if raw is None and default is _UNSET:
        raise KeyError(f"Didn't found user with id = {tg_id}")
    elif raw is None:
        return default

    user = parse_user(raw)
    return user


async def _get_users() -> list[UserInfo]:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(f"""SELECT {",".join(USER_KEYS)} FROM {TABLE_NAME}""", ())
        result_: Any = await cur.fetchall()
    result = list(result_) if result_ is not None else list()

    return [parse_user(raw) for raw in result if raw]


async def _update_user(
    tg_id: int,
    blacklist: str | Iterable[str | int] | None | Any = _UNSET,
    pts: int | None | Any = _UNSET,
    ts: int | None | Any = _UNSET,
    pinned_message_id: int | None | Any = _UNSET,
):
    values: dict[
        Literal[
            "blacklist",
            "pts",
            "ts",
            "pinned_message_id",
        ],
        Any,
    ] = dict()
    if blacklist is not _UNSET:
        b_list = blacklist if blacklist is not None else ""
        b_list = [b_list] if isinstance(b_list, (str, int)) else b_list
        blacklist_glob = _srl_blacklist(b_list)
        values["blacklist"] = blacklist_glob
    if pts is not _UNSET:
        values["pts"] = pts
    if ts is not _UNSET:
        values["ts"] = ts
    if pinned_message_id is not _UNSET:
        values["pinned_message_id"] = pinned_message_id

    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET {", ".join("{}=?".format(x) for x in values.keys())} WHERE tg_id=?""",
            (
                *values.values(),
                tg_id,
            ),
        )
        await con.commit()


async def _delete_user(
    tg_id: int,
):
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""DELETE FROM {TABLE_NAME} WHERE tg_id=?""",
            (tg_id,),
        )
        await con.commit()


def _srl_blacklist(items: str | int | Iterable[str | int]) -> bytes:
    if len(str(items)) == 0:
        return b""
    items = [items] if isinstance(items, (str, int)) else items
    return gzip.compress(_BLACKLIST_SEP.join(str(i) for i in items).encode("utf-8"))


def _drl_blacklist(item: bytes) -> set[str | int]:
    if not item:
        return set()
    tmp = set(
        int(i) if i.removeprefix("-").isdigit() else i
        for i in gzip.decompress(item).decode("utf-8").split(_BLACKLIST_SEP)
    )
    return tmp


async def _set_blacklist(tg_id: int, items: Iterable[str | int]) -> None:
    item = _srl_blacklist(items)
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET blacklist=? WHERE tg_id=?""",
            (
                item,
                tg_id,
            ),
        )
        await con.commit()
    return None


async def _get_blacklist(tg_id: int) -> None | set[str | int]:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT blacklist FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,)
        )
        result = await cur.fetchone()  # : tuple[bytes] | None
    to_return: set[str | int] | None = (
        _drl_blacklist(result[0]) if result is not None else None
    )
    return to_return


async def _get_token(tg_id: int) -> None | str:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT vk_token FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,)
        )
        result = await cur.fetchone()  # : tuple[str] | None
    to_return_ = tuple(result) if result is not None else None
    to_return: str | None = to_return_[0] if isinstance(to_return_, tuple) else None
    return to_return


async def _set_token(tg_id: int, vk_token: str) -> None | str:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET vk_token=? WHERE tg_id=?""",
            (
                vk_token,
                tg_id,
            ),
        )
        await con.commit()
    return None


async def _get_state(tg_id: int) -> None | bool:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT polling_state FROM {TABLE_NAME} WHERE tg_id=?""",
            (tg_id,),
        )
        result = await cur.fetchone()  # : tuple[int] | None
    to_return_ = tuple(result) if result is not None else None
    to_return: bool | None = (
        bool(to_return_[0]) if isinstance(to_return_, tuple) else None
    )
    return to_return


async def _set_state(tg_id: int, polling_state: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET polling_state=? WHERE tg_id=?""",
            (
                int(polling_state),
                tg_id,
            ),
        )
        await con.commit()
    return None


async def _get_longpoll_state(tg_id: int) -> tuple[bool, int, int] | None:
    """returns (polling_state, pts, ts) or None"""
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT polling_state, pts, ts FROM {TABLE_NAME} WHERE tg_id=?""",
            (tg_id,),
        )
        result = await cur.fetchone()  # : tuple[bool, int, int] | None
    to_return = tuple(result) if result is not None else None
    # state = bool(result[0]),
    return to_return


async def _set_longpoll_state(
    tg_id: int, polling_state: bool, pts: int, ts: int
) -> None:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET polling_state=?, pts=?, ts=? WHERE tg_id=?""",
            (
                int(polling_state),
                pts,
                ts,
                tg_id,
            ),
        )
        await con.commit()
        # result = await cur.fetchone()  # : tuple[bool, int, int] | None
    # to_return = tuple(result) if result is not None else None
    # return to_return


async def _get_polling_state(tg_id: int) -> bool | None:
    """returns polling_state or None"""
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT polling_state FROM {TABLE_NAME} WHERE tg_id=?""",
            (tg_id,),
        )
        result = await cur.fetchone()  # : tuple[bool, int, int] | None
    to_return = tuple(result)[0] if result is not None else None
    return to_return


async def _set_polling_state(tg_id: int, polling_state: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET polling_state=? WHERE tg_id=?""",
            (
                int(polling_state),
                tg_id,
            ),
        )
        await con.commit()


class UserSettingsManager:
    tg_id: int

    class BaseManager(ABC):
        parent: "UserSettingsManager"

        def __init__(self, parent: "UserSettingsManager"):
            self.parent = parent

        @abstractmethod
        async def get(self) -> ...: ...

    class StateManager(BaseManager):
        async def get(self):
            return await _get_state(self.parent.tg_id)

        async def set(self, value: bool):
            return await _set_state(tg_id=self.parent.tg_id, polling_state=value)

    class LongPollingStateManager(BaseManager):
        async def get(self):
            return await _get_longpoll_state(tg_id=self.parent.tg_id)

        async def set(self, value: bool, pts: int, ts: int):
            return await _set_longpoll_state(
                tg_id=self.parent.tg_id, polling_state=value, pts=pts, ts=ts
            )

    class PollingStateManager(StateManager):
        async def get(self):
            return await _get_polling_state(tg_id=self.parent.tg_id)

        async def set(self, value: bool):
            return await _set_polling_state(
                tg_id=self.parent.tg_id, polling_state=value
            )

    class TokenManager(BaseManager):
        async def get(self):
            return await _get_token(tg_id=self.parent.tg_id)

        async def set(self, vk_token):
            return await _set_token(tg_id=self.parent.tg_id, vk_token=vk_token)

    class BlacklistManager(BaseManager):
        async def get(self):
            return await _get_blacklist(tg_id=self.parent.tg_id)

        async def set(self, items: Iterable[str | int]):
            return await _set_blacklist(tg_id=self.parent.tg_id, items=items)

    class UserManager(BaseManager):
        async def get(self, tg_id: int | Any = _UNSET):
            if tg_id is _UNSET:
                return await _get_user(tg_id=self.parent.tg_id)
            elif isinstance(tg_id, int):
                return await _get_user(tg_id=tg_id)
            raise TypeError(
                f"Excepted ID or unset for tg_id, got {type(tg_id)}!",
                type(tg_id),
            )

        @staticmethod
        async def get_all():
            return await _get_users()

        async def set(
            self,
            blacklist: str | Iterable[str | int] | Any | None = _UNSET,
            pts: int | Any | None = _UNSET,
            ts: int | Any | None = _UNSET,
            pinned_message_id: int | Any | None = _UNSET,
        ):
            return await _update_user(
                tg_id=self.parent.tg_id,
                blacklist=blacklist,
                pinned_message_id=pinned_message_id,
                pts=pts,
                ts=ts,
            )

        async def delete(self):
            return await _delete_user(tg_id=self.parent.tg_id)

        async def create(self, vk_token: str):
            return await _init_user(tg_id=self.parent.tg_id, vk_token=vk_token)

    user: UserManager
    blacklist: BlacklistManager
    token: TokenManager
    state: StateManager
    longpoll_state: LongPollingStateManager
    polling_state: PollingStateManager

    def __init__(self, tg_id: int):
        self.tg_id = tg_id
        self.user = UserSettingsManager.UserManager(self)
        self.blacklist = UserSettingsManager.BlacklistManager(self)
        self.token = UserSettingsManager.TokenManager(self)
        self.state = UserSettingsManager.StateManager(self)
        self.longpoll_state = UserSettingsManager.LongPollingStateManager(self)
        self.polling_state = UserSettingsManager.PollingStateManager(self)


async def test():
    uid = -100
    test_vk_token = ""
    blacklist_item1 = "something"
    BLACKLIST2 = ""
    manager = UserSettingsManager(uid)
    user_manager = manager.user

    usr = await _get_user(tg_id=uid, default=None)
    if usr is None:
        await user_manager.create(vk_token=test_vk_token)
    else:
        print(f"! {usr=}")
    await user_manager.set(blacklist=blacklist_item1)

    usr = await user_manager.get()
    assert blacklist_item1 in usr.blacklist, f"{usr.blacklist=}"
    await user_manager.set(blacklist=BLACKLIST2)

    usr = await user_manager.get()
    assert len(usr.blacklist) == 0, f"{usr.blacklist=}"
    await user_manager.delete()

    usr = await _get_user(tg_id=uid, default=None)
    assert usr is None, f"{usr=}"


NOTSET = object()

if __name__ == "__main__":
    asyncio.run(test())

__all__ = ["UserSettingsManager", "init_db"]
