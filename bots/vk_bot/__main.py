from utils.config import CHATS_BLACKLIST, Config
from vk_api.vk_api import VkApiMethod
from vk_api.longpoll import VkEventType, Event
import vk_api.longpoll  # type: ignore[import-untyped]

from .. import telegram_bot
from . import my_functions as functions
from .handlers import (
    on_message_edit,
    on_message_new,
    on_message_react,
    on_message_read,
    on_message_read_self,
    on_message_type,
    on_other_event,
    on_update_counter,
    on_flag_interacted,
)
from .utils import beautify_print
import datetime
import logging


logger = logging.getLogger(__name__)


cache: dict[str, dict[tuple, dict]] = {
    "profiles_list_to_dict": {},
    "groups_list_to_dict": {},
    "conversations_list_to_dict": {},
}


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


def handle_(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles: list[dict] | None = None,
    conversations: list[dict] | None = None,
    groups: list[dict] | None = None,
) -> bool:
    chat_id = getattr(event, "chat_id", None)
    profiles_ = profiles_list_to_dict(profiles) if profiles else {}
    conversations_ = conversations_list_to_dict(conversations) if conversations else {}
    groups_ = groups_list_to_dict(groups) if groups else {}
    chat = (
        functions.get_conversation_info_by_chat_id(api, chat_id)[0] if chat_id else None
    )
    # beautify_print(event)
    if event.type in [
        601,
        602,
    ]:
        # print(event.peer_id, event.type)
        return False

    if chat and chat.strip() in CHATS_BLACKLIST:
        return False

    if event.type == VkEventType.MESSAGE_NEW:
        beautify_print(event)
        on_message_new(event, api, tg_client, profiles_, conversations_, groups_)

    elif event.type in (VkEventType.USER_TYPING_IN_CHAT, VkEventType.USER_TYPING):
        # beautify_print(event)
        on_message_type(event, api, tg_client, profiles_, conversations_, groups_)

    elif event.type == VkEventType.MESSAGE_EDIT:
        beautify_print(event)
        on_message_edit(event, api, tg_client, profiles_, conversations_, groups_)

    elif event.type == VkEventType.READ_ALL_OUTGOING_MESSAGES:
        on_message_read(event, api, tg_client, profiles_, conversations_, groups_)

    elif event.type == VkEventType.READ_ALL_INCOMING_MESSAGES:
        beautify_print(event)
        on_message_read_self(event, api, tg_client, profiles_, conversations_, groups_)

    # elif event.type == VkEventType.MESSAGES_COUNTER_UPDATE:
    #     on_update_counter(event, api, tg_client)

    elif event.type in {
        VkEventType.MESSAGE_FLAGS_RESET,
        VkEventType.MESSAGE_FLAGS_REPLACE,
        VkEventType.MESSAGE_FLAGS_SET,
    }:
        on_flag_interacted(event, api, tg_client)

    else:
        beautify_print(event)
        on_other_event(event, api, tg_client, profiles_, conversations_, groups_)
    print()
    return True


from ..telegram_bot.classes import MyTelegram
import traceback
import logging
import vk_api
import time

from requests.exceptions import ConnectionError, Timeout

from utils.my_longpoll import (
    get_longpoll,
    load_longpoll_info,
    save_longpoll_info,
    get_last_vk_id,
)
from utils.interface.vk_messages import get_tg_id


logger = logging.getLogger(__name__)
TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError)


def log(text: str) -> None:
    """like logger.info, but doesn't log via logger"""
    import datetime

    print(f"{str(datetime.datetime.now())[:-3]} - [UNKNOWN] - main.py - {text}")


def send_to_tg(tgClient: MyTelegram, text: str):
    BLOCK_SIZE = 4000
    blocks = [
        text[BLOCK_SIZE * i : BLOCK_SIZE * (i + 1)]
        for i in range(0, len(text) // BLOCK_SIZE)
    ]

    logger.debug(f"{blocks=}")
    for block in blocks:
        tgClient.send_text(f"<blockquote expandable>{block}</blockquote>")


def get_old_messages(
    api: VkApiMethod,
    vk_longpoll: vk_api.longpoll.VkLongPoll,
    tg_client: MyTelegram,
) -> None:
    chat_id = tg_client.CHAT_ID
    max_msg_id = get_last_vk_id(chat_id)
    result: dict = {"more": 1}
    index = 0
    while "more" in result and result["more"]:
        result = api.messages.getLongPollHistory(
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

        profiles = result.get("profiles", [])
        groups = result.get("groups", [])
        conversations = result.get("conversations", [])
        history: list[list] = iter(result["history"].copy())
        del result["history"], result["credentials"]  # for less logs

        for event in history:
            logger.debug(f"getLongPollHistory - {event=}")
            # beautify_print(event)
            if event[0] in {4, 5}:
                msg_ = api.messages.getById(message_ids=event[1])["items"]
                if not msg_:
                    continue
                msg = msg_[0]
                to_new_event = event + [msg["date"], msg["text"]]
                fake_event = Event(to_new_event)
            else:
                fake_event = Event(event)
            
            handle(fake_event, api, tg_client)
            index += 1

        vk_longpoll.server = server
        vk_longpoll.ts = ts
        vk_longpoll.key = key
        vk_longpoll.pts = pts
        save_longpoll_info(tg_client.CHAT_ID, vk_longpoll, log=True)

    if index:
        log(f"Processed {index} updates")


def main(chat_id: int):
    vk_client, vk_longpoll = get_longpoll(chat_id)
    api = vk_client.get_api()

    tg_client = MyTelegram(chat_id)
    logger.info(f"On server:\n  ts: {vk_longpoll.ts}\n  pts: {vk_longpoll.pts}")
    server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts

    load_longpoll_info(chat_id, vk_longpoll)
    vk_longpoll.update_longpoll_server(update_ts=False)
    logger.info(f"Saved:\n  ts: {vk_longpoll.ts}\n  pts: {vk_longpoll.pts}")
    if server_pts and server_pts - vk_longpoll.pts > 0:
        logger.info(f"Bot is getting last {server_pts-vk_longpoll.pts} messages")
        logger.debug(f"{(server_ts or 0)-(vk_longpoll.ts or -1) =}")
        get_old_messages(api, vk_longpoll, tg_client)
    else:
        logger.info(f"Bot is up-to-date with server :3")

    # exit()
    tg_client.send_text("Бот запущен!")
    logger.info("Бот запущен!")

    while True:
        try:
            index = 0
            events = vk_longpoll.check()
            for event in events:
                need_to_log = handle(event, api, tg_client)
                if need_to_log:
                    index += 1
                    logger.debug(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")
            if index:
                save_longpoll_info(chat_id, vk_longpoll, log=False)
                log(f"Processed {index} updates")
                logger.debug(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")

        except KeyboardInterrupt:
            tg_client.stop()
            break

        except TIMEOUT_EXCEPTIONS:
            logger.warning("timeout")
            time.sleep(1)

    save_longpoll_info(chat_id, vk_longpoll, log=True)
    logger.info(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")


def handle(
    event: Event,
    api: VkApiMethod,
    tg_client: MyTelegram,
    profiles: list[dict] | None = None,
    conversations: list[dict] | None = None,
    groups: list[dict] | None = None,
    _retries=5,
) -> bool:
    def handle_exception(ex: Exception):
        error_str = "".join(traceback.format_exception(ex))
        send_to_tg(tg_client, error_str)
        time.sleep(1)
        send_to_tg(tg_client, f"Событие: {event!r}")
        logger.error(error_str)

    try:
        return handle_(event, api, tg_client, profiles, conversations, groups)
    except vk_api.exceptions.ApiError as ex:
        if _retries > 0:
            time.sleep(1)
            return handle(event, api, tg_client, _retries=_retries - 1)
        handle_exception(ex)
        return False

    except Exception as ex:
        handle_exception(ex)
        return False
