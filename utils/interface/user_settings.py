from pydantic import BaseModel, Field
from typing import Iterable, Any, overload
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


async def add_user(tg_id: int, vk_token: str):
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""INSERT INTO {TABLE_NAME} (tg_id, polling_state, vk_token, blacklist) VALUES (?, 0, ?, ?)""",
            (tg_id, vk_token, b""),
        )
        await con.commit()


@overload
async def get_user[T](tg_id: int, default: T) -> UserInfo | T: ...
@overload
async def get_user(tg_id: int, default: Any = _UNSET) -> UserInfo: ...
async def get_user[T](tg_id: int, default: T | Any = _UNSET) -> UserInfo | T:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(f"""SELECT * FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,))
        result = await cur.fetchone()  # : tuple | None

    if result is None and default is _UNSET:
        raise KeyError(f"Didn't found user with id = {tg_id}")
    elif result is None:
        return default

    k = "tg_id,polling_state,vk_token,blacklist,pts,ts".split(",")
    d = {k: v for (k, v) in zip(k, result)}
    user = UserInfo(**d)
    # user.()
    return user


async def get_users() -> list[UserInfo]:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(f"""SELECT * FROM {TABLE_NAME}""", ())
        result_: Any = await cur.fetchall()  # : list[tuple]
    result = list(result_) if result_ is not None else list()
    
    keys = "tg_id,polling_state,vk_token,blacklist,pts,ts".split(",")
    # keys: list[str] = list(UserInfo.model_fields.keys())
    raw_list = [
        {key: value for (key, value) in zip(keys, values)}
        for values in result
        if values
    ]
    users = [UserInfo(**d) for d in raw_list]
    return users


async def save_user(
    tg_id: int,
    # polling_state: bool = False,
    # vk_token: str = "",
    items: Iterable[str | int] | None = None,
    pts: int = 0,
    ts: int = 0,
):
    item = _srl_blacklist(items or [""])
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""UPDATE {TABLE_NAME} SET blacklist=?, pts=?, ts=? WHERE tg_id=?""",
            (
                item,
                pts,
                ts,
                tg_id,
            ),
        )
        await con.commit()

def _srl_blacklist(items: Iterable[str | int]) -> bytes:
    if not items:
        return b""
    return gzip.compress(_BLACKLIST_SEP.join([str(i) for i in items]).encode("utf-8"))


def _drl_blacklist(item: bytes) -> set[str | int]:
    if not item:
        return set()
    tmp = set(int(i) if i.removeprefix("-").isdigit() else i for i in gzip.decompress(item).decode("utf-8").split(_BLACKLIST_SEP))
    return tmp


async def set_blacklist(tg_id: int, items: Iterable[str | int]) -> None:
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


async def get_blacklist(tg_id: int) -> None | set[str | int]:
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


async def get_token(tg_id: int) -> None | str:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT vk_token FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,)
        )
        result = await cur.fetchone()  # : tuple[str] | None
    to_return_ = tuple(result) if result is not None else None
    to_return: str | None = to_return_[0] if isinstance(to_return_, tuple) else None
    return to_return


async def get_state(tg_id: int) -> None | bool:
    async with aiosqlite.connect(DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT polling_state FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,)
        )
        result = await cur.fetchone()  # : tuple[int] | None
    to_return_ = tuple(result) if result is not None else None
    to_return: bool | None = (
        bool(to_return_[0]) if isinstance(to_return_, tuple) else None
    )
    return to_return


async def set_state(tg_id: int, polling_state: bool) -> None:
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


async def get_longpoll_state(tg_id: int) -> tuple[bool, int, int] | None:
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


async def set_longpoll_state(
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


async def get_polling_state(tg_id: int) -> bool | None:
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


async def set_polling_state(
        tg_id: int, polling_state: bool
) -> None:
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


async def test():
    UID = -100
    VK_TOKEN = ""
    BLACKLIST1 = "something"
    BLACKLIST2 = ""
    await add_user(UID, "")


if __name__ == "__main__":
    asyncio.run(test())
