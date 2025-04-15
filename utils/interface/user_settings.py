from pydantic import BaseModel, Field
from typing import Iterable
import sqlite3
import pathlib
import gzip


class UserInfo(BaseModel):
    tg_id: int
    pooling_state: bool = False
    vk_token: str = ""
    blacklist_: bytes | None = Field(alias="blacklist")
    pts: int = 0
    ts: int = 0

    @property
    def blacklist(self) -> set[str]:
        return _drl_blacklist(self.blacklist_ or b"")


_DB_PATH = ["data", "database.db"]
TABLE_NAME = "UserInfo"

DB_PATH = str(pathlib.Path(*_DB_PATH))
_BLACKLIST_SEP = "•"


with sqlite3.connect(DB_PATH) as con:
    cur = con.cursor()
    cur.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
tg_id INTEGER PRIMARY KEY,
pooling_state INTEGER,
vk_token TEXT,
blacklist BLOB,
pts INTEGER,
ts INTEGER
)"""
    )
    con.commit()


def add_user(tg_id: int, vk_token: str):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""INSERT INTO {TABLE_NAME} (tg_id, pooling_state, vk_token, blacklist) VALUES (?, 0, ?, ?)""",
            (tg_id, vk_token, b""),
        )
        con.commit()


def get_user(tg_id: int) -> UserInfo:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f"""SELECT * FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,))
        result: tuple | None = cur.fetchone()
    if result is None:
        raise KeyError(f"Didn't found user with id = {tg_id}")
    k = "tg_id,pooling_state,vk_token,blacklist,pts,ts".split(",")
    d = {k: v for (k, v) in zip(k, result)}
    user = UserInfo(**d)
    # user.()
    return user


def save_user(
    tg_id: int,
    # pooling_state: bool = False,
    # vk_token: str = "",
    items: Iterable[str] | None = None,
    pts: int = 0,
    ts: int = 0,
):
    item = _srl_blacklist(items or [""])
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""UPDATE {TABLE_NAME} SET blacklist=?, pts=?, ts=? WHERE tg_id=?""",
            (
                item,
                pts,
                ts,
                tg_id,
            ),
        )
        con.commit()
    pass


def _srl_blacklist(items: Iterable[str]) -> bytes:
    if not items:
        return b""
    return gzip.compress(_BLACKLIST_SEP.join(items).encode("utf-8"))


def _drl_blacklist(item: bytes) -> set[str]:
    if not item:
        return set()
    return set(gzip.decompress(item).decode("utf-8").split(_BLACKLIST_SEP))


def set_blacklist(tg_id: int, items: Iterable[str]) -> None:
    item = _srl_blacklist(items)
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""UPDATE {TABLE_NAME} SET blacklist=? WHERE tg_id=?""",
            (
                item,
                tg_id,
            ),
        )
        con.commit()
    return None


def get_blacklist(tg_id: int) -> None | set[str]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f"""SELECT blacklist FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,))
        result_: tuple[bytes] | None = cur.fetchone()
    result: set[str] | None = (
        _drl_blacklist(result_[0]) if result_ is not None else None
    )
    return result


def get_token(tg_id: int) -> None | str:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(f"""SELECT vk_token FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,))
        _result: tuple[str] | None = cur.fetchone()
        result: str | None = _result and _result[0]
    return result


def get_state(tg_id: int) -> None | bool:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""SELECT pooling_state FROM {TABLE_NAME} WHERE tg_id=?""", (tg_id,)
        )
        _result: tuple[int] | None = cur.fetchone()
        result: bool | None = _result and bool(_result[0])
    return result


def set_state(tg_id: int, pooling_state: bool) -> None:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""UPDATE {TABLE_NAME} SET pooling_state=? WHERE tg_id=?""",
            (
                int(pooling_state),
                tg_id,
            ),
        )
        con.commit()
    return None


def get_longpoll_state(tg_id: int) -> tuple[bool, int, int] | None:
    """returns (pooling_state, pts, ts)"""
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""SELECT pooling_state, pts, ts FROM {TABLE_NAME} WHERE tg_id=?""",
            (tg_id,),
        )
        result: tuple[bool, int, int] | None = cur.fetchone()
    return result


def set_longpoll_state(
    tg_id: int, pooling_state: bool, pts: int, ts: int
) -> tuple[bool, int, int] | None:
    """returns (pooling_state, pts, ts)"""
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""UPDATE {TABLE_NAME} SET pooling_state=?, pts=?, ts=? WHERE tg_id=?""",
            (
                int(pooling_state),
                pts,
                ts,
                tg_id,
            ),
        )
        result: tuple[bool, int, int] | None = cur.fetchone()
    return result


def test():
    UID = -100
    VK_TOKEN = ""
    BLACKLIST1 = "something"
    BLACKLIST2 = ""
    add_user(UID, "")


if __name__ == "__main__":
    test()
