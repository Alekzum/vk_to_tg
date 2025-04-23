from typing import NamedTuple, Any
import aiosqlite
import sqlite3
import pathlib


class MyPair(NamedTuple):
    tg_id: int
    vk_ig: int


DB_PATH = ["data", "database.db"]
TABLE_NAME = "Messages"

_DB_PATH = str(pathlib.Path(*DB_PATH))


async def init_db():
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
    tg_msg_id INTEGER NOT NULL,
    tg_chat_id INTEGER NOT NULL,
    vk_id INTEGER NOT NULL
    )"""
        )
        await con.commit()


async def add_pair(tg_msg_id: int, tg_chat_id: int, vk_id: int):
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""INSERT INTO {TABLE_NAME} (tg_msg_id, tg_chat_id, vk_id) VALUES (?, ?, ?)""",
            (
                tg_msg_id,
                tg_chat_id,
                vk_id,
            ),
        )
        await con.commit()


async def get_vk_id(tg_msg_id: int, tg_chat_id: int) -> None | int:
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT vk_id FROM {TABLE_NAME} WHERE tg_msg_id=? AND tg_chat_id=?""",
            (
                tg_msg_id,
                tg_chat_id,
            ),
        )
        result = await cur.fetchone()  # : tuple[int] | None
    to_return_ = tuple(result) if result is not None else None
    to_return: int | None = to_return_[0] if isinstance(to_return_, tuple) else None
    return to_return


async def get_tg_id(tg_chat_id: int, vk_id: int) -> None | int:
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT tg_msg_id FROM {TABLE_NAME} WHERE (vk_id=? AND tg_chat_id=?)""",
            (
                vk_id,
                tg_chat_id,
            ),
        )
        result = await cur.fetchone()
    to_return_ = tuple(result) if result is not None else None
    to_return: int | None = to_return_[0] if isinstance(to_return_, tuple) else None
    return to_return


async def get_last_vk_id(tg_chat_id: int) -> None | int:
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"SELECT vk_id FROM {TABLE_NAME} WHERE tg_chat_id=? AND vk_id = (SELECT MAX(vk_id) FROM {TABLE_NAME})",
            (tg_chat_id,),
        )
        result = await cur.fetchone()
    to_return_ = tuple(result) if result is not None else None
    to_return: int | None = to_return_[0] if isinstance(to_return_, tuple) else None
    return to_return


async def get_all_ids(tg_chat_id: int) -> None | list[MyPair]:
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"SELECT tg_msg_id, vk_id FROM {TABLE_NAME} WHERE tg_chat_id=?", (tg_chat_id,)
        )
        result = await cur.fetchall()  # : list[tuple[int, int]]
    # to_return_ = tuple(result) if result is not None else None
    # to_return: str | None = to_return_[0] if isinstance(to_return_, tuple) else None
    to_return = [MyPair(*p) for p in result]
    return to_return
