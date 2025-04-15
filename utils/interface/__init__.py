# from . import vk_messages
# from . import user_settings
# from vk_api.longpoll import Event
# from vk_api.vk_api import VkApiMethod
# from typing import Literal, cast


# import pathlib
# import sqlite3


# DB_PATH = ["data", "database.db"]
# # TABLE_NAME = "VkMessages"

# _DB_PATH = str(pathlib.Path(*DB_PATH))



# with sqlite3.connect(_DB_PATH) as con:
#     cur = con.cursor()
#     cur.execute(f'''CREATE TABLE IF NOT EXISTS {TABLE_NAME}(
# message_id INTEGER PRIMARY KEY,
# peer_id INTEGER NOT NULL
# )''')
#     con.commit()



# def make_pair(tg_msg_id: int, tg_chat_id: int, vk_msg: Event) -> tuple[Literal[True], None]:
#     """Make pair tg message<->vk message. Can be used with user's reply to tg message"""
#     vk_msg_id = cast(int, vk_msg.message_id)
#     vk_peer_id = cast(int, vk_msg.peer_id)
#     vk_messages.add_pair(tg_msg_id, tg_chat_id, vk_msg_id)
#     with sqlite3.connect(_DB_PATH) as con:
#         cur = con.cursor()
#         cur.execute(f'''INSERT INTO {TABLE_NAME} (message_id, peer_id) VALUES (?, ?)''', (vk_msg_id, vk_peer_id))
#         con.commit()
#     # um... peer_id can be fetched with messages.getById... ok, let's call it "making requests/seconds lower"
#     return True, None


# def get_vk_message(tg_msg_id: int, tg_chat_id: int, api: VkApiMethod) -> Event:
#     vk_msg_id = vk_messages.get_vk_id(tg_msg_id, tg_chat_id)
#     if vk_msg_id is None:
#         raise KeyError(f"Didn't found vk_message paired with {(tg_msg_id, tg_chat_id)=}")

#     with sqlite3.connect(_DB_PATH) as con:
#         cur = con.cursor()
#         cur.execute(f'''SELECT FROM {TABLE_NAME} * WHERE message_id=?''', (vk_msg_id, ))
#         fetch_result: tuple[int, int] = cur.fetchone()
#     peer_id, msg_id = fetch_result
    
#     get_result: dict = api.messages.getById(messages_ids=str(msg_id))
#     response = get_result.get('response')
#     if response is None:
#         raise TypeError(f"Invalid response: {get_result}")

#     items = response['items']
#     if not items:
#         raise ValueError(f"Message with that ID doesn't exists")
    
#     result_raw = items[0]
#     result = Event(result_raw)
#     return result
