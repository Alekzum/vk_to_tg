from aiogram.fsm.storage.base import (
    BaseStorage,
    StorageKey,
    StateType,
    DefaultKeyBuilder,
    KeyBuilder,
)
from aiogram.fsm.state import State
from typing import Any, Dict, Optional

import aiosqlite
import sqlite3
import pickle
import json

import logging

logger = logging.getLogger(__name__)


class AioSQLStorage(BaseStorage):
    def __init__(
        self,
        db_path: str = "fsm_storage.db",
        serializing_method: str = "pickle",
        key_builder: Optional[KeyBuilder] = None,
    ) -> None:
        """
        You can point a database path. It will be 'fsm_storage.db' for default.
        It's possible to choose srtializing method: 'pickle' (default) or 'json'.
        If you hange serializing method, you shoud delete existing database,
        and start a new one. 'Pickle' is slower than 'json', but it can serialize
        some kind of objects, that 'json' cannot. 'Pickle' creates unreadable
        for human data in database, instead of 'json'.
        """
        self._init_db(db_path)

        self.key_builder = key_builder or DefaultKeyBuilder(
            with_bot_id=True, with_destiny=True
        )
        self._db_path = db_path
        self._ser_m = serializing_method

        if self._ser_m != "pickle" and self._ser_m != "json":
            logger.warning(
                f"'{self._ser_m}' is unknown serializing method! A 'pickle' will be used."
            )
            self._ser_m = "pickle"

    def _init_db(self, db_path):
        with sqlite3.connect(db_path) as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS fsm_data (key TEXT PRIMARY KEY, state TEXT, data TEXT)"
            )
            con.commit()

    def _key(self, key: StorageKey) -> str:
        """
        Create a key for every uniqe user, chat and bot
        """
        result_string = self.key_builder.build(key)
        return result_string

    def _ser(self, obj: object) -> str | bytes | None:
        """
        Serialize object
        """
        if self._ser_m == "json":
            return json.dumps(obj)

        return pickle.dumps(obj)

    def _dsr(self, obj) -> Dict[str, Any]:
        """
        Deserialize object
        """

        if self._ser_m == "json":
            return json.loads(obj) or {}

        return pickle.loads(obj) or {}

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        """
        Set state for specified key

        :param key: storage key
        :param state: new state
        """
        s_key = self._key(key)
        s_state = state.state if isinstance(state, State) else state

        async with aiosqlite.connect(self._db_path) as con:
            cursor = await con.cursor()
            await cursor.execute(
                "INSERT OR REPLACE INTO fsm_data (key, state, data) VALUES (?, ?, COALESCE((SELECT data FROM fsm_data WHERE key = ?), NULL));",
                (s_key, s_state, s_key),
            )
            await con.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        """
        Get key state

        :param key: storage key
        :return: current state
        """
        s_key = self._key(key)

        async with aiosqlite.connect(self._db_path) as con:
            cursor = await con.cursor()
            await cursor.execute("SELECT state FROM fsm_data WHERE key = ?", (s_key,))
            s_state = await cursor.fetchone()

        if s_state and len(s_state) > 0:
            return s_state[0]
        else:
            return None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """
        Write data (replace)

        :param key: storage key
        :param data: new data
        """
        s_key = self._key(key)
        s_data = self._ser(data)

        async with aiosqlite.connect(self._db_path) as con:
            cursor = await con.cursor()
            await cursor.execute(
                "INSERT OR REPLACE INTO fsm_data (key, state, data) VALUES (?, COALESCE((SELECT state FROM fsm_data WHERE key = ?), NULL), ?);",
                (s_key, s_key, s_data),
            )
            await con.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        """
        Get current data for key

        :param key: storage key
        :return: current data
        """
        s_key = self._key(key)

        async with aiosqlite.connect(self._db_path) as con:
            cursor = await con.cursor()
            await cursor.execute("SELECT data FROM fsm_data WHERE key = ?", (s_key,))
            s_data = await cursor.fetchone()
        if s_data is None:
            return {}

        return self._dsr(s_data[0])

    async def close(self) -> None:
        """
        Close storage (database connection, file or etc.)
        """
        pass
