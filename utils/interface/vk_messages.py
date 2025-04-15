from typing import NamedTuple, Any
import sqlite3
import pathlib


class MyPair(NamedTuple):
    tg_id: int
    vk_ig: int


DB_PATH = ["data", "database.db"]
TABLE_NAME = "Messages"

_DB_PATH = str(pathlib.Path(*DB_PATH))


with sqlite3.connect(_DB_PATH) as con:
    cur = con.cursor()
    cur.execute(
        f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
tg_msg_id INTEGER NOT NULL,
tg_chat_id INTEGER NOT NULL,
vk_id INTEGER NOT NULL
)"""
    )
    con.commit()


def add_pair(tg_msg_id: int, tg_chat_id: int, vk_id: int):
    with sqlite3.connect(_DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""INSERT INTO {TABLE_NAME} (tg_msg_id, tg_chat_id, vk_id) VALUES (?, ?, ?)""",
            (
                tg_msg_id,
                tg_chat_id,
                vk_id,
            ),
        )
        con.commit()


def get_vk_id(tg_msg_id: int, tg_chat_id: int) -> None | int:
    with sqlite3.connect(_DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""SELECT vk_id FROM {TABLE_NAME} WHERE tg_msg_id=? AND tg_chat_id=?""",
            (
                tg_msg_id,
                tg_chat_id,
            ),
        )
        _result: tuple[int] | None = cur.fetchone()
        result: int | None = _result and _result[0]
    return result


def get_tg_id(tg_chat_id: int, vk_id: int) -> None | int:
    with sqlite3.connect(_DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"""SELECT tg_msg_id FROM {TABLE_NAME} WHERE (vk_id=? AND tg_chat_id=?)""",
            (
                vk_id,
                tg_chat_id,
            ),
        )
        result = cur.fetchone()
        result = result and result[0]
    return result


def get_last_vk_id(tg_chat_id: int) -> None | int:
    with sqlite3.connect(_DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"SELECT vk_id FROM {TABLE_NAME} WHERE tg_chat_id=? AND vk_id = (SELECT MAX(vk_id) FROM {TABLE_NAME})",
            (tg_chat_id,),
        )
        result = cur.fetchone()
        result = result and result[0]
    return result


def get_all_ids(tg_chat_id: int) -> None | list[MyPair]:
    with sqlite3.connect(_DB_PATH) as con:
        cur = con.cursor()
        cur.execute(
            f"SELECT tg_msg_id, vk_id FROM {TABLE_NAME} WHERE tg_chat_id=?", (tg_chat_id,)
        )
        result_: list[tuple[int, int]] = cur.fetchall()
        result = [MyPair(*p) for p in result_]
    return result
