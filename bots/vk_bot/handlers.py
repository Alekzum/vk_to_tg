from utils.my_classes import TgMessage
from utils.interface.vk_messages import get_tg_id, add_pair

from .. import telegram_bot
from .utils import (
    get_message_info,
    get_message_string,
    get_pair_for_dict,
    get_from_user,
    get_in_chat,
    get_from_peer,
    get_reaction,
    get_tg_id,
    beautify_print,
)
from .my_functions import get_dialog_name
from .classes import Message
import logging

from vk_api.longpoll import Event, VkEventType, VkMessageFlag
from vk_api.vk_api import VkApiMethod
from itertools import accumulate
from typing import Callable
import pickle
import pathlib


logger = logging.getLogger(__name__)

messages_cache: dict[tuple[int, int], str] = dict()
full_messages_cache: dict[tuple[int, int], Event] = dict()
binds_vk_to_tg: dict[int, int] = dict()
flags_cache: dict[int, set[VkMessageFlag]] = dict()

caches = dict(
    messages_cache=messages_cache,
    full_messages_cache=full_messages_cache,
    binds_vk_to_tg=binds_vk_to_tg,
    flags_cache=flags_cache,
)

caches_file = pathlib.Path(__file__).parent.joinpath("data", "caches.pkl")


def load_caches():
    if not caches_file.parent.exists():
        caches_file.parent.mkdir()
    if not caches_file.exists():
        caches_file.write_bytes(b"")

    raw = caches_file.read_bytes()
    if not raw:
        return
    
    global caches
    new_caches = pickle.loads(raw)
    caches = {i: new_caches[i] for i in caches.copy()}
    globals().update(caches)


def save_caches():
    caches_file.write_bytes(pickle.dumps(caches))


def on_message_edit(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    chat_id = tg_client.CHAT_ID

    pair_for_dict = get_pair_for_dict(event)
    if (msg_data := getattr(event, "message_data", {})) and "reaction_id" in msg_data:
        return on_message_react(
            event, api, tg_client, profiles_, conversations_, groups_
        )

    text, isInBlocklist = get_message_string(event, api)
    if isInBlocklist:
        return

    time, msg_info = get_message_info(event, api)
    _previous_message = messages_cache.get(pair_for_dict) if pair_for_dict else None
    # string = f"Redacted message {time} {msg_info}: {event.message}\n * Previous message was {repr(_previous_message) or '*неизвестно*'}"
    string = f"Redacted message {text}\n * Previous message was {_previous_message or '*unknown*'}"
    if pair_for_dict:
        messages_cache[pair_for_dict] = event.message

    logger.info(string)

    if event.message_id and (tg_id := get_tg_id(chat_id, event.message_id)):
        tg_client.reply_text(msg_id=int(tg_id), text=string)
    else:
        tg_client.send_text(string)


def on_message_new(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    # _handle_new_message(event, api, tg)
    chat_id = tg_client.CHAT_ID

    flags_cache[event.message_id] = event.flags

    text, isInBlocklist = get_message_string(event, api)

    pair_for_dict = get_pair_for_dict(event)
    if pair_for_dict:
        messages_cache[pair_for_dict] = event.message
        full_messages_cache[pair_for_dict] = event

    if not isInBlocklist:
        logger.info(text)
    else:
        print(text)
        return

    if vk_id := getattr(event, "reply_message", {}).get("id"):
        msg = tg_client.reply_text(text=text, msg_id=get_tg_id(chat_id, vk_id))
    else:
        msg = tg_client.send_text(text)

    if isinstance(msg, TgMessage) and event.message_id:
        binds_vk_to_tg[event.message_id] = msg.id
        add_pair(msg.id, chat_id, event.message_id)

    elif event.message_id:
        logger.warning(f"{msg!r}")


def on_message_read(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    chat_id = tg_client.CHAT_ID
    chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    string = f"Read all outgoing messages in chat {chat}"

    logger.info(string)

    if event.message_id and (tg_id := get_tg_id(chat_id, event.message_id)):
        tg_client.reply_text(msg_id=int(tg_id), text=string)
    else:
        tg_client.send_text(string)


def on_message_read_self(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    chat_id = tg_client.CHAT_ID
    chat = get_dialog_name(
        api,
        getattr(event, "peer_id")
    )
    # chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    string = f"Read all incoming messages in chat {chat}"

    logger.info(string)

    if event.message_id and (tg_id := get_tg_id(chat_id, event.message_id)):
        tg_client.reply_text(msg_id=int(tg_id), text=string)
    else:
        tg_client.send_text(string)


def on_message_react(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    chat_id = tg_client.CHAT_ID
    chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    string = f"Read all outgoing messages in chat {chat}"

    logger.info(string)

    if event.message_id and (tg_id := get_tg_id(chat_id, event.message_id)):
        tg_client.reply_text(msg_id=int(tg_id), text=string)
    else:
        tg_client.send_text(string)


def on_message_type(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    from_user = get_from_user(api, event, profiles_)
    in_chat = get_in_chat(api, event, conversations_, groups_)

    string = f"""In chat {in_chat!r}({event.peer_id}) {from_user!r} is typing..."""
    logger.info(string)


def on_update_counter(
    event: Event, api: VkApiMethod, tg_client: telegram_bot.classes.MyTelegram
):
    string = f"Unread messages count: {event.count}"  # type: ignore[reportAttributeAccessIssue]
    # because it's always integer
    tg_client.send_text(string)


def on_flag_interacted(
    event: Event, api: VkApiMethod, tg_client: telegram_bot.classes.MyTelegram
):
    assert event.message_id, "wtf - event with message's flag, but message_id is none"
    logger.debug(f"{beautify_print(event, need_to_print=False, indent=None)}")

    chat_id = tg_client.CHAT_ID
    mask = getattr(event, "mask")

    get_flags = lambda mask: {flag for flag in VkMessageFlag if mask & flag == flag}
    string_flags = lambda flags: ', '.join({i.name for i in flags})
    # mask 8 & flag 9 != 9
    
    if event.type in {VkEventType.MESSAGE_FLAGS_REPLACE, VkEventType.MESSAGE_FLAGS_SET}:
        new_flags = mask
        flags = get_flags(new_flags)
        string = f"Флаги у сообщения: {string_flags(flags)}"
        flags_cache[event.message_id] = new_flags

    elif event.type == VkEventType.MESSAGE_FLAGS_RESET:
        old_flags = get_flags(flags_cache.get(event.message_id, 0))
        flags = get_flags(mask)
        diff = flags
        result_mask = old_flags - flags
        string = f"Убранные флаги у сообщения: {string_flags(diff)}\nТекущие флаги сообщения: {string_flags(result_mask)}"

    else:
        raise

    save_caches()

    logger.info(string)

    if event.message_id and (tg_id := get_tg_id(chat_id, event.message_id)):
        tg_client.reply_text(msg_id=int(tg_id), text=string)
    else:
        tg_client.send_text(string)
    # tg_client.send_text(string)


def on_other_event(
    event: Event,
    api: VkApiMethod,
    tg_client: telegram_bot.classes.MyTelegram,
    profiles_: dict,
    conversations_: dict,
    groups_: dict,
):
    from_user = get_from_user(api, event, profiles_)
    in_chat = get_in_chat(api, event, conversations_, groups_)

    event_display_name = event.type.name if hasattr(event.type, "name") else event.type

    event_all_args = event.__dict__
    # event_all_args = " | ".join(
    #     [
    #         "event.{}: {}".format(n, getattr(event, n))
    #         for n in dir(event)
    #         if n[0] != "_" and bool(getattr(event, n))
    #     ]
    # )
    logger.info(
        f"{event_display_name}, {from_user=!r}, {in_chat=!r}, | {event_all_args} | "
    )
