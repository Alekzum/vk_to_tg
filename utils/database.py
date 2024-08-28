import sqlite3
import os


dbPath = os.sep.join("data", "database.db")


with sqlite3.connect(dbPath) as con:
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS Messages(
tg_id INTEGER PRIMARY KEY,
vk_id INTEGER NOT NULL
)''')
    con.commit()


def add_pair(tg_id: int, vk_id: int):
    with sqlite3.connect(dbPath) as con:
        cur = con.cursor()
        cur.execute('''INSERT INTO Messages (tg_id, vk_id) VALUES (?, ?)''', (tg_id, vk_id,))
        con.commit()


def get_vk_id(tg_id: int) -> None | int:
    with sqlite3.connect(dbPath) as con:
        cur = con.cursor()
        cur.execute('''SELECT vk_id FROM Messages WHERE tg_id=?''', (tg_id,))
        result = cur.fetchone()
        result = result and result [0]
    return result


def get_tg_id(vk_id: int) -> None | int:
    with sqlite3.connect(dbPath) as con:
        cur = con.cursor()
        cur.execute('''SELECT tg_id FROM Messages WHERE vk_id=?''', (vk_id,))
        result = cur.fetchone()
        result = result and result [0]
    return result