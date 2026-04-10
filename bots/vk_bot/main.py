from utils.config import OWNER_ID
from utils.my_vk_api import VkApiMethod, AsyncVkLongPoll
from utils.my_longpoll import (
    get_client_and_longpoll,
    load_longpoll_info,
    save_longpoll_info,
    get_last_vk_id,
)
from vk_api.longpoll import VkEventType, Event

from requests.exceptions import ConnectionError, Timeout
from httpx import NetworkError, TimeoutException, RemoteProtocolError

from .. import telegram_bot
from .my_async_functions import get_dialog_name

from . import handlers
from .utils import beautify_print
from ..telegram_bot.classes import MyTelegram
from utils.interface.user_settings import get_polling_state, set_polling_state

from utils.my_logging import getLogger
import asyncio
import traceback
import vk_api
from html import escape

from io import BytesIO


logger = getLogger(__name__)
TIMEOUT_EXCEPTIONS = (
    Timeout,
    ConnectionError,
    NetworkError,
    TimeoutException,
    RemoteProtocolError,
)


cache: dict[str, dict[tuple, dict]] = {
    "profiles_list_to_dict": {},
    "groups_list_to_dict": {},
    "conversations_list_to_dict": {},
}


def log(text: str) -> None:
    # """like logger.info, but doesn't log via logger :clueless:"""
    logger.debug(f"{text}")


async def send_to_tg(
    tgClient: MyTelegram, text: str, chat_id: int | None = None, block_size=4000
):
    logger.debug(f"{text}")
    chat_id = chat_id or tgClient.chat_id

    if len(text) > block_size:
        current_file = BytesIO(text.encode("utf-8"))
        current_file.name = "big_message.txt"

        await tgClient.tg.send_document(
            chat_id=chat_id,
            document=current_file,
            caption=f"Часть содержимого файла: <blockquote expandable><code>{text[:256]}</code>...</blockquote>",
        )
    blocks = [
        text[block_size * i : block_size * (i + 1)]
        for i in range(0, (len(text) // block_size) + 1)
    ]

    for block in blocks:
        await tgClient.tg.send_message(
            chat_id=chat_id,
            text=f"<blockquote expandable><code>{escape(block)}</code></blockquote>",
        )


def profiles_list_to_dict(src: list[dict]) -> dict[int, dict]:
    cache_: dict = cache["profiles_list_to_dict"]
    key = tuple([repr(item) for item in src])
    return cache_.get(
        key, cache_.setdefault(key, {profile["id"]: profile for profile in src})
    )


def groups_list_to_dict(src: list[dict]) -> dict[int, dict]:
    cache_: dict = cache["groups_list_to_dict"]
    key = tuple([repr(item) for item in src])
    return cache_.get(
        key, cache_.setdefault(key, {group["id"]: group for group in src})
    )


def conversations_list_to_dict(src: list[dict]) -> dict[int, dict]:
    cache_: dict = cache["conversations_list_to_dict"]
    key = tuple([repr(item) for item in src])
    return cache_.get(
        key, cache_.setdefault(key, {chat["peer"]["id"]: chat for chat in src})
    )


async def handle_(
    event: Event, api: VkApiMethod, tg_client: telegram_bot.classes.MyTelegram
) -> bool:
    """uh...

    Args:
        event (Event): just event
        api (VkApiMethod): user's API
        tg_client (telegram_bot.classes.MyTelegram): user's tg client

    Returns:
        bool: Is chat in blacklist
    """

    def print_if_its_me(obj):
        return beautify_print(obj) if tg_client.chat_id == OWNER_ID else None

    if event.type in {601, 602}:
        return False

    await tg_client.config.load_values()

    peer_id: int | None = getattr(event, "peer_id", None)
    if peer_id:
        if peer_id in tg_client.config.blacklist:
            return False
        logger.debug("peed id is not in blacklist", peer_id=peer_id)
        peer_name = handlers.chats_cache.get(
            peer_id, await get_dialog_name(api, peer_id)
        )
        if peer_name is not None:
            handlers.chats_cache[peer_id] = peer_name
            if peer_name in tg_client.config.blacklist:
                return False
            logger.debug("peer name is not in blacklist", peer_name=peer_name)

    # peer_id = getattr(event, "chat_id", None)
    # chat_id: int
    if chat_id := round(getattr(event, "chat_id", 0) + 2e9):
        if chat_id in tg_client.config.blacklist:
            return False

        chat = await get_dialog_name(api, chat_id) if chat_id else None
        if chat in tg_client.config.blacklist:
            return False

    logger.debug(
        "Handling new event",
        event_object=event,
        event_type=event.type,
        raw_event=event.__dict__,
    )
    if event.type == VkEventType.MESSAGE_NEW:
        print_if_its_me(event)
        await handlers.on_message_new(event, api, tg_client)

    elif event.type == VkEventType.USER_TYPING:
        await handlers.on_user_typing(event, api, tg_client)

    elif event.type == VkEventType.USER_TYPING_IN_CHAT:
        await handlers.on_user_typing_in_chat(event, api, tg_client)

    elif event.type == VkEventType.MESSAGE_EDIT:
        print_if_its_me(event)
        await handlers.on_message_edit(event, api, tg_client)

    elif event.type == VkEventType.READ_ALL_OUTGOING_MESSAGES:
        await handlers.on_real_all_outgoing_messages(event, api, tg_client)

    elif event.type == VkEventType.READ_ALL_INCOMING_MESSAGES:
        print_if_its_me(event)
        await handlers.on_read_all_incoming_messages(event, api, tg_client)

    elif event.type == VkEventType.MESSAGES_COUNTER_UPDATE:
        await handlers.on_unread_messages_counter_update(event, api, tg_client)

    # elif event.type in {
    #     VkEventType.MESSAGE_FLAGS_RESET,
    #     VkEventType.MESSAGE_FLAGS_REPLACE,
    #     VkEventType.MESSAGE_FLAGS_SET,
    # }:
    #     await on_message_flag_interacted(event, api, tg_client)

    else:
        print_if_its_me(event)
        await handlers.on_other_event(event, api, tg_client)
    print()
    return True


async def get_old_messages(
    api: VkApiMethod,
    vk_longpoll: AsyncVkLongPoll,
    tg_client: MyTelegram,
) -> None:
    user_id = tg_client.chat_id
    max_msg_id = await get_last_vk_id(user_id)
    result: dict = {"more": 1}
    index = 0
    while "more" in result and result["more"]:
        result = await api.messages.getLongPollHistory(
            ts=vk_longpoll.ts,
            pts=vk_longpoll.pts,
            lp_version=3,
            credentials=True,
            max_msg_id=max_msg_id,
        )
        server = result["credentials"]["server"]
        ts = result["credentials"]["ts"]
        key = result["credentials"]["key"]
        pts = result["new_pts"]

        history: list[list] = iter(result["history"].copy())

        for event in history:
            # logger.debug(f"getLongPollHistory - {event=}")
            if event[0] in {4, 5}:
                msg_ = (await api.messages.getById(message_ids=event[1]))[
                    "items"
                ]
                if not msg_:
                    continue
                msg = msg_[0]
                to_new_event = event + [msg["date"], msg["text"]]
                fake_event = Event(to_new_event)
            else:
                fake_event = Event(event)

            await handle(fake_event, api, tg_client)
            if tg_client.chat_id == OWNER_ID:
                logger.debug(f"getLongPollHistory - {event=}, {fake_event=}")
            index += 1
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break

        vk_longpoll.server = server
        vk_longpoll.ts = ts
        vk_longpoll.key = key
        vk_longpoll.pts = pts
        await save_longpoll_info(tg_client.chat_id, vk_longpoll, log=True)

    if index:
        logger.debug(f"Processed {index} updates", user_id=user_id)


async def handle(
    event: Event, api: VkApiMethod, tg_client: MyTelegram, _retries=5
) -> bool:
    """uh... handle event and except ApiError

    Args:
        event (Event): just event
        api (VkApiMethod): user's API
        tg_client (telegram_bot.classes.MyTelegram): user's tg client

    Returns:
        bool: Is chat in blacklist
    """

    async def handle_exception(ex: Exception):
        error_str = "".join(traceback.format_exception(ex))

        logger.error(error_str)
        logger.debug(error_str)
        await send_to_tg(
            tg_client, error_str + "\n" + escape(f"Событие: {event!r}")
        )
        # logger.error(error_str)

    try:
        return await handle_(event, api, tg_client)
    except vk_api.exceptions.ApiError as ex:
        if _retries > 0:
            await asyncio.sleep(1)
            return await handle(event, api, tg_client, _retries=_retries - 1)
        await handle_exception(ex)
        return False

    # except Exception as ex:
    #     await handle_exception(ex)
    #     return False


async def main(user_id: int):
    logger.debug("Получение вк клиента и longpoll'а...", user_id=user_id)
    vk_client, vk_longpoll = await get_client_and_longpoll(user_id)
    api = vk_client.get_api()

    tg_client = MyTelegram(user_id, "VkAPI2TgBot")
    logger.debug("Бот стартует...", user_id=user_id)
    await tg_client.init()

    await vk_longpoll.update_longpoll_server(update_ts=True)
    server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts
    logger.info("On server", ts=server_ts, pts=server_pts, user_id=user_id)
    server_ts = server_ts if isinstance(server_ts, int) else 32

    await load_longpoll_info(user_id, vk_longpoll)
    logger.info(
        "Saved", ts=vk_longpoll.ts, pts=vk_longpoll.pts, user_id=user_id
    )
    # if server_ts <
    logger.info(
        f"Bot is getting last {server_ts - (vk_longpoll.ts if isinstance(vk_longpoll.ts, int) else 32)} events",
        user_id=user_id,
    )
    await get_old_messages(api, vk_longpoll, tg_client)

    server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts
    await set_polling_state(user_id, True)
    await tg_client.send_text("Бот запущен!")
    logger.info("Бот запущен!", user_id=user_id)

    while await get_polling_state(user_id):
        try:
            index = 0
            events = await vk_longpoll.check()
            for event in events:
                need_to_log = await handle(event, api, tg_client)
                if need_to_log:
                    index += 1
                    logger.debug(
                        "ts+pts",
                        ts=vk_longpoll.ts,
                        pts=vk_longpoll.pts,
                        user_id=user_id,
                        index=index,
                    )

                await asyncio.sleep(0)
            if index:
                await save_longpoll_info(user_id, vk_longpoll, log=False)
                logger.debug(f"Processed {index} updates", user_id=user_id)
                if user_id == OWNER_ID:
                    logger.info(
                        "ts+pts",
                        ts=vk_longpoll.ts,
                        pts=vk_longpoll.pts,
                        user_id=user_id,
                    )

        except KeyboardInterrupt:
            logger.info("set polling state to False")
            await set_polling_state(user_id, False)

        except TIMEOUT_EXCEPTIONS as ex:
            logger.warning("timeout")
            logger.debug(f"timeout, {ex=}")
            await asyncio.sleep(10)

        except Exception as ex:
            trace = traceback.format_exc()

            public_trace = f"Возникла ошибка. {ex}"
            private_trace = f"{user_id=}, traceback: {trace}"

            logger.warning("Exception!", ex=ex, user_id=user_id)
            print(private_trace)
            logger.debug(private_trace, exc_info=True, user_id=user_id)
            await tg_client.send_text(public_trace)
            await send_to_tg(tg_client, text=private_trace, chat_id=OWNER_ID)

        try:
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            break

    await tg_client.stop()

    await save_longpoll_info(user_id, vk_longpoll, log=True)
    logger.info(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")
