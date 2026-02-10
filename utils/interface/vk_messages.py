from typing import NamedTuple
import aiosqlite
import pathlib
from utils.my_logging import getLogger


class MyPair(NamedTuple):
    tg_id: int
    tg_chat_id: int
    vk_ig: int
    is_sferum: int


DB_PATH = ["data", "database.db"]
TABLE_NAME = "Messages"

_DB_PATH = str(pathlib.Path(*DB_PATH))
logger = getLogger(__name__)


async def init_db():
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
    tg_msg_id INTEGER NOT NULL,
    tg_chat_id INTEGER NOT NULL,
    vk_id INTEGER NOT NULL,
    is_sferum INTEGER DEFAULT 0
)"""
        )
        await con.commit()


async def add_pair(
    tg_msg_id: int, tg_chat_id: int, vk_id: int, is_sferum: bool = False
):
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""INSERT INTO {TABLE_NAME} (tg_msg_id, tg_chat_id, vk_id, is_sferum) VALUES (?, ?, ?, ?)""",
            (tg_msg_id, tg_chat_id, vk_id, int(is_sferum)),
        )
        await con.commit()


async def get_vk_id(
    tg_msg_id: int, tg_chat_id: int, is_sferum: bool = False
) -> int | None:
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"""SELECT vk_id FROM {TABLE_NAME} WHERE tg_msg_id=? AND tg_chat_id=? AND is_sferum=?""",
            (tg_msg_id, tg_chat_id, int(is_sferum)),
        )
        result = await cur.fetchone()  # : tuple[int] | None
    logger.debug(f"{result=}")
    if result is None:
        return None
    to_return_: tuple[int] = tuple(result)
    to_return: int = to_return_[0]
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
    if result is None:
        return None
    to_return_ = tuple(result)
    to_return: int = to_return_[0]
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
    to_return: int | None = (
        to_return_[0] if isinstance(to_return_, tuple) else None
    )
    return to_return


async def get_all_ids(tg_chat_id: int) -> None | list[MyPair]:
    async with aiosqlite.connect(_DB_PATH) as con:
        cur = await con.cursor()
        await cur.execute(
            f"SELECT * FROM {TABLE_NAME} WHERE tg_chat_id=?",
            (tg_chat_id,),
        )
        result = await cur.fetchall()  # : list[tuple[int, int]]
    # to_return_ = tuple(result) if result is not None else None
    # to_return: str | None = to_return_[0] if isinstance(to_return_, tuple) else None
    to_return = [MyPair(*p) for p in result]
    return to_return
