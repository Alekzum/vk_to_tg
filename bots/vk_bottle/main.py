from utils.config import OWNER_ID
# from utils.my_vk_api import API, AsyncVkLongPoll
from utils.my_longpoll import (
    # get_client_and_longpoll,
    load_longpoll_info,
    save_longpoll_info,
    get_last_vk_id,
)
# from vk_api.longpoll import VkEventType, Event  # type: ignore

from requests.exceptions import ConnectionError, Timeout
from httpx import NetworkError, TimeoutException
from .. import telegram_bot
from .my_async_functions import get_dialog_name

# from .handlers import (
#     on_message_edit,
#     on_message_new,
#     on_message_react,
#     on_real_all_outgoing_messages,
#     on_read_all_incoming_messages,
#     on_user_typing_in_chat,
#     on_other_event,
#     on_message_counter_update,
#     on_message_flag_interacted,
#     chats_cache,
# )
from .utils import beautify_print
from ..telegram_bot.classes import MyTelegram
# from utils.interface.vk_messages import get_tg_id
from utils.interface.user_settings import get_polling_state, set_polling_state
from utils.config import Config
from vkbottle_types.events.user_events import RawUserEvent

import structlog
from utils.my_logging import getLogger
import logging
import asyncio
import traceback
import structlog
from utils.my_logging import getLogger
import logging
import vkbottle


logger = getLogger(__name__)
TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError, NetworkError, TimeoutException)


cache: dict[str, dict[tuple, dict]] = {
    "profiles_list_to_dict": {},
    "groups_list_to_dict": {},
    "conversations_list_to_dict": {},
}


def log(text: str) -> None:
    """like logger.info, but doesn't log via logger"""
    import datetime

    logger.debug(f"{text}")


async def send_to_tg(tgClient: MyTelegram, text: str):
    BLOCK_SIZE = 4000
    blocks = [
        text[BLOCK_SIZE * i : BLOCK_SIZE * (i + 1)]
        for i in range(0, len(text) // BLOCK_SIZE)
    ]

    logger.debug(f"{blocks=}")
    for block in blocks:
        await tgClient.send_text(f"<blockquote expandable>{block}</blockquote>")


# def profiles_list_to_dict(src: list[dict]) -> dict[int, dict]:
#     cache_: dict = cache["profiles_list_to_dict"]
#     key = tuple([repr(item) for item in src])
#     return cache_.get(
#         key, cache_.setdefault(key, {profile["id"]: profile for profile in src})
#     )


# def groups_list_to_dict(src: list[dict]) -> dict[int, dict]:
#     cache_: dict = cache["groups_list_to_dict"]
#     key = tuple([repr(item) for item in src])
#     return cache_.get(
#         key, cache_.setdefault(key, {group["id"]: group for group in src})
#     )


# def conversations_list_to_dict(src: list[dict]) -> dict[int, dict]:
#     cache_: dict = cache["conversations_list_to_dict"]
#     key = tuple([repr(item) for item in src])
#     return cache_.get(
#         key, cache_.setdefault(key, {chat["peer"]["id"]: chat for chat in src})
#     )


# async def handle_(
#     event: Event, api: API, tg_client: telegram_bot.classes.MyTelegram
# ) -> bool:
#     """uh...

#     Args:
#         event (Event): just event
#         api (API): user's API
#         tg_client (telegram_bot.classes.MyTelegram): user's tg client

#     Returns:
#         bool: Is chat in blacklist
#     """

#     def print_if_its_me(obj):
#         return beautify_print(obj) if tg_client.CHAT_ID == OWNER_ID else None

#     if event.type in {601, 602}:
#         return False

#     await tg_client.config.load_values()

#     peer_id: int | None = getattr(event, "peer_id", None)
#     if peer_id:
#         if peer_id in tg_client.config._blacklist:
#             return False
#         logger.debug(f"{peer_id=}")
#         peer_name = chats_cache.get(peer_id, await get_dialog_name(api, peer_id))
#         if peer_name is not None:
#             chats_cache[peer_id] = peer_name
#             if peer_name in tg_client.config._blacklist:
#                 return False
#             logger.debug(f"{peer_name=}")

#     # peer_id = getattr(event, "chat_id", None)
#     # chat_id: int
#     if chat_id := round(getattr(event, "chat_id", 0) + 2e9):
#         if chat_id in tg_client.config._blacklist:
#             return False

#         chat = await get_dialog_name(api, chat_id) if chat_id else None
#         if chat in tg_client.config._blacklist:
#             return False

#     if event.type == VkEventType.MESSAGE_NEW:
#         print_if_its_me(event)
#         await on_message_new(event, api, tg_client)

#     elif event.type in (VkEventType.USER_TYPING_IN_CHAT, VkEventType.USER_TYPING):
#         await on_user_typing_in_chat(event, api, tg_client)

#     elif event.type == VkEventType.MESSAGE_EDIT:
#         print_if_its_me(event)
#         await on_message_edit(event, api, tg_client)

#     elif event.type == VkEventType.READ_ALL_OUTGOING_MESSAGES:
#         await on_real_all_outgoing_messages(event, api, tg_client)

#     elif event.type == VkEventType.READ_ALL_INCOMING_MESSAGES:
#         print_if_its_me(event)
#         await on_read_all_incoming_messages(event, api, tg_client)

#     elif event.type == VkEventType.MESSAGES_COUNTER_UPDATE:
#         await on_message_counter_update(event, api, tg_client)

#     elif event.type in {
#         VkEventType.MESSAGE_FLAGS_RESET,
#         VkEventType.MESSAGE_FLAGS_REPLACE,
#         VkEventType.MESSAGE_FLAGS_SET,
#     }:
#         await on_message_flag_interacted(event, api, tg_client)

#     else:
#         print_if_its_me(event)
#         await on_other_event(event, api, tg_client)
#     print()
#     return True


# async def handle(
#     event: Event, api: API, tg_client: MyTelegram, _retries=5
# ) -> bool:
#     """uh...

#     Args:
#         event (Event): just event
#         api (API): user's API
#         tg_client (telegram_bot.classes.MyTelegram): user's tg client

#     Returns:
#         bool: Is chat in blacklist
#     """

#     async def handle_exception(ex: Exception):
#         error_str = "".join(traceback.format_exception(ex))
#         await send_to_tg(tg_client, error_str)
#         await asyncio.sleep(1)
#         await send_to_tg(tg_client, f"Событие: {event!r}")
#         logger.error(error_str)

#     try:
#         return await handle_(event, api, tg_client)
#     except vk_api.exceptions.ApiError as ex:
#         if _retries > 0:
#             await asyncio.sleep(1)
#             return await handle(event, api, tg_client, _retries=_retries - 1)
#         await handle_exception(ex)
#         return False

#     # except Exception as ex:
#     #     await handle_exception(ex)
#     #     return False


async def get_old_messages(
    vk_bot: vkbottle.User,
    # vk_longpoll: vkbottle.UserPolling,
    tg_client: MyTelegram,
) -> None:
    user_id = tg_client.CHAT_ID
    config = Config(user_id)
    await config.load_values()

    max_msg_id = await get_last_vk_id(user_id)
    result: dict = {"more": 1}

    index = 0
    kwargs = dict(
        ts=config.ts,
        pts=config.pts,
        lp_version=3,
        credentials=True,
        max_msg_id=max_msg_id,
    )
    while "more" in result and result["more"]:
        result = await vk_bot.api.request("messages.getLongPollHistory", kwargs)
        
        server = result["credentials"]["server"]
        ts = result["credentials"]["ts"]
        key = result["credentials"]["key"]
        pts = result["new_pts"]

        history: list[list] = iter(result["history"].copy())  # lazy iterator

        for event in history:
            if event[0] in {4, 5}:
                msg_ = (await vk_bot.api.request("messages.getById", dict(message_ids=event[1])))["items"]
                if not msg_:
                    continue
                msg = msg_[0]
                to_new_event = event + [msg["date"], msg["text"]]
                # fake_event = Event(to_new_event)
                fake_event = to_new_event
            else:
                # fake_event = Event(event)
                fake_event = event

            event = await vk_bot.polling.get_event(result["credentials"])
            # (fake_event, vk_bot.api)
            await vk_bot.router.route(event, vk_bot.api)
            if tg_client.CHAT_ID == OWNER_ID:
                logger.debug(f"getLongPollHistory - {event=}, {fake_event=}")
            index += 1
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break

        config._set_ts(ts)
        config._set_pts(pts)
        await config.save_values()

        kwargs = dict(
            ts=config.ts,
            pts=config.pts,
            lp_version=3,
            credentials=True,
            max_msg_id=max_msg_id,
        )

    if index:
        logger.debug(f"{user_id=}, Processed {index} updates")


async def main(user_id: int):
    logger.debug(f"{user_id=}, Получение вк клиента и longpoll'а...")
    config = Config(user_id)
    await config.load_values()
    user_token = config._ACCESS_TOKEN

    vk_api = vkbottle.API(token=user_token)
    vk_polling = vkbottle.UserPolling(api=vk_api)
    vk_bot = vkbottle.User(api=vk_api, polling=vk_polling)

    # vk_bot.on.raw_event()
    
    tg_client = MyTelegram(user_id)
    logger.debug(f"{user_id=}, Бот стартует...")
    await tg_client.init()

    if vk_polling.user_id is None:
        vk_polling.user_id = (await vk_api.request("users.get", {}))["response"][0][
            "id"
        ]
    server = (await vk_api.request("messages.getLongPollServer", dict(need_pts=1)))[
        "response"
    ]

    server_ts, server_pts = server["ts"], server["pts"]
    logger.info(f"{user_id=}, On server: ts={server_ts}, pts={server_pts}")

    logger.info(f"{user_id=}, Saved: ts={config.ts}, pts={config.pts}")
    logger.info(f"{user_id=}, Bot is getting last {server_pts-config.pts} events")
    await get_old_messages(vk_bot, tg_client)

    vk_api.
    # vk_bot.on.raw_event()
    # server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts
    # await set_polling_state(user_id, True)
    # await tg_client.send_text("Бот запущен!")
    # logger.info(f"{user_id=}, Бот запущен!")

    # while await get_polling_state(user_id):
    #     try:
    #         index = 0
    #         events = await vk_longpoll.check()
    #         for event in events:
    #             need_to_log = await handle(event, api, tg_client)
    #             if need_to_log:
    #                 index += 1
    #                 logger.debug(
    #                     f"{user_id=}, ts={vk_longpoll.ts}, pts={vk_longpoll.pts}"
    #                 )
    #             await asyncio.sleep(0)
    #         if index:
    #             await save_longpoll_info(user_id, vk_longpoll, log=False)
    #             logger.debug(f"{user_id=}, Processed {index} updates")
    #             if user_id == OWNER_ID:
    #                 logger.info(
    #                     f"{user_id=}, ts={vk_longpoll.ts}, pts={vk_longpoll.pts}"
    #                 )

    #     except KeyboardInterrupt:
    #         logger.info("set polling state to False")
    #         await set_polling_state(user_id, False)

    #     except TIMEOUT_EXCEPTIONS as ex:
    #         logger.warning("timeout")
    #         logger.debug(f"timeout, {ex=}")

    #     except Exception as ex:
    #         logger.warning(f"{ex=}")
    #         raise ex

    #     try:
    #         await asyncio.sleep(1)
    #     except asyncio.CancelledError:
    #         break

    # await tg_client.stop()

    # await save_longpoll_info(user_id, vk_longpoll, log=True)
    # logger.info(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")
