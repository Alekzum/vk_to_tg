# from utils.my_classes import TgMessage

# from utils.interface.vk_messages import get_tg_id, add_pair

from .. import telegram_bot
# from utils.my_vk_api import vkbottle.API
from .utils import get_pair_for_dict, get_tg_id, add_pair, get_message_url
from .my_async_functions import (
    parse_event,
    get_user_name,
    get_chat_name,
    get_dialog_name,
)
import structlog
from utils.my_logging import getLogger
import logging

# from vk_api.longpoll import Event, VkEventType, VkMessageFlag  # type: ignore
from typing import TypedDict, Any, Iterable, overload
# from vkbottle_types.events import Event
from vkbottle_types.events.user_events import RawUserEvent as Event
import vkbottle
import pathlib
import pickle

from pydantic import BaseModel, Field


class Cache[KEY, VALUE](BaseModel):
    items: dict[KEY, VALUE] = Field(default_factory=lambda: dict())


class Caches(TypedDict):
    messages_cache: dict[tuple[int, int], str]
    full_messages_cache: dict[tuple[int, int], Event]
    binds_vk_to_tg: dict[int, int]
    flags_cache: dict[int, int]
    chats_cache: dict[int, str]


logger = getLogger(__name__)

messages_cache: dict[tuple[int, int], str] = dict()
full_messages_cache: dict[tuple[int, int], Event] = dict()
binds_vk_to_tg: dict[int, int] = dict()
flags_cache: dict[int, int] = dict()
chats_cache: dict[int, str] = dict()

caches: Caches = Caches(
    messages_cache=messages_cache,
    full_messages_cache=full_messages_cache,
    binds_vk_to_tg=binds_vk_to_tg,
    flags_cache=flags_cache,
    chats_cache=chats_cache,
)

caches_file = pathlib.Path(__file__).parent.joinpath("data", "caches.pkl")
_last_update_string = ""


def logger_info(string) -> None:
    logger.info(repr(string))
    print(string)


def logger_debug(string) -> None:
    logger.debug(repr(string))
    print(string)


def get_caches() -> Caches:
    return caches


def load_caches() -> None:
    if not caches_file.parent.exists():
        caches_file.parent.mkdir()
    if not caches_file.exists():
        caches_file.write_bytes(b"")

    raw = caches_file.read_bytes()
    if not raw:
        return

    global caches
    new_caches: dict[str, Any] = pickle.loads(raw)
    caches = Caches(**{i: new_caches.get(i, dict()) for i in caches.copy()})  # type: ignore
    globals().update(caches)


def save_caches() -> None:
    caches_file.write_bytes(pickle.dumps(caches))


async def edit_message(
    # event: Event,
    tg_client: telegram_bot.classes.MyTelegram,
    string: str,
    vk_id_: int | None = None,
    tg_id_: int | None = None,
    append: bool = False,
) -> None:
    chat_id = tg_client.CHAT_ID
    if vk_id_:
        tg_id = await get_tg_id(chat_id, vk_id_)
        if tg_id is None:
            raise KeyError("Didn't found tg_id with this vk_id!")
    elif tg_id_:
        tg_id = tg_id_
    else:
        raise ValueError("Use vk_id or tg_id")

    msg = await tg_client.get_messages(tg_id)
    if msg.empty:
        return

    if msg.text is None:
        raise ValueError(f"Didn't found text at message with id {msg.id}; {msg=}")

    await tg_client.edit_text(
        tg_id, (msg.text.markdown + "\n" + string) if append else string
    )


async def send_to_chat(
    event: Event,
    tg_client: telegram_bot.classes.MyTelegram,
    string: str,
    save: bool = True,
) -> None:
    chat_id = tg_client.CHAT_ID

    if (vk_msg_id := getattr(event, "message_id", None)) and (
        tg_id := await get_tg_id(chat_id, vk_msg_id)
    ):
        msg = await tg_client.reply_text(msg_id=int(tg_id), text=string)
    else:
        msg = await tg_client.send_text(string)

    if not save:
        return

    if msg and event.message_id:
        binds_vk_to_tg[event.message_id] = msg.id
        await add_pair(msg.id, chat_id, event.message_id)

    elif event.message_id:
        logger.warning(f"{msg!r} (caused with {string=})")


async def on_message_edit(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
) -> None:
    chat_id = tg_client.CHAT_ID

    pair_for_dict = get_pair_for_dict(event)
    msg_data = getattr(event, "message_data", {})
    if msg_data and "reaction_id" in msg_data:
        return await on_message_react(event, api, tg_client)

    text, isInBlocklist = await parse_event(event, api)
    if isInBlocklist:
        return

    _previous_message = messages_cache.get(pair_for_dict) if pair_for_dict else None
    # string = f"Redacted message {time} {msg_info}: {event.message}\n * Previous message was {repr(_previous_message) or '*неизвестно*'}"
    string = f"Redacted message {text}\n * Previous message was {_previous_message or '*unknown*'}"
    if pair_for_dict:
        messages_cache[pair_for_dict] = event.message

    logger_info(string)

    await send_to_chat(event, tg_client, string)


async def on_message_new(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
):
    # _handle_new_message(event, api, tg)
    chat_id = tg_client.CHAT_ID
    # assert isinstance(event.message_id, int)

    flags_cache[event.message_id] = event.flags  # type: ignore[reportArgumentType]
    # vk_api < vkbottle. maybe at one great day...

    string, isInBlocklist = await parse_event(event, api)

    pair_for_dict = get_pair_for_dict(event)
    if pair_for_dict:
        messages_cache[pair_for_dict] = event.message
        full_messages_cache[pair_for_dict] = event

    if not isInBlocklist:
        logger_info(string)
    else:
        logger_debug(string)
        return

    await send_to_chat(event, tg_client, string)


async def on_real_all_outgoing_messages(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
):
    chat_id = tg_client.CHAT_ID
    # chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    chat = await get_dialog_name(api, event.peer_id)  # type: ignore
    string = f"Read all outgoing messages in chat {chat}"

    logger_info(string)

    await send_to_chat(event, tg_client, string)


async def on_read_all_incoming_messages(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
) -> None:
    # chat_id = tg_client.CHAT_ID
    # chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    chat = await get_dialog_name(api, event.peer_id)  # type: ignore
    string = f"Read all incoming messages in chat {chat}"

    logger_info(string)

    await send_to_chat(event, tg_client, string)


async def on_message_react(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
) -> None:
    chat_id = tg_client.CHAT_ID
    chat = await get_dialog_name(api, event.peer_id)  # type: ignore
    # chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    string = f"Read all outgoing messages in chat {chat}"

    logger_info(string)

    await send_to_chat(event, tg_client, string)


async def on_user_typing_in_chat(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
) -> None:
    chat_id = getattr(event, "chat_id") + 2000000000  # because it's chat
    from_user = await get_dialog_name(api, event.user_id)  # type: ignore
    in_chat = await get_dialog_name(api, chat_id)  # type: ignore
    # from_user = get_from_user(api, event, profiles_)
    # in_chat = get_in_chat(api, event, conversations_, groups_)

    string = f"""In chat {in_chat!r}({chat_id}) {from_user!r} is typing..."""
    d = {k: v for (k, v) in event.__dict__.items() if k[0] != "_"}
    logger_debug(f"{d} - {string}")


async def on_message_counter_update(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
) -> None:
    global _last_update_string
    string = f"Unread messages count: {event.count}"  # type: ignore
    # because it's always integer
    if _last_update_string != string:
        await tg_client.send_text(string)
        _last_update_string = string


# def get_flags(mask: int) -> set[VkMessageFlag]:
#     return {flag for flag in VkMessageFlag if mask & flag == flag}


# def string_flags(flags: set[VkMessageFlag]):
#     return ", ".join({i.name for i in flags})


# async def on_message_flag_interacted(
#     event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
# ) -> None:
#     assert event.message_id, "wtf - event with message's flag, but message_id is none"
#     # logger.debug(f"{beautify_print(event, need_to_print=False, indent=None)}")

#     # chat_id = tg_client.CHAT_ID
#     mask = getattr(event, "mask")

#     # mask 8 & flag 9 != 9

#     if event.type in {VkEventType.MESSAGE_FLAGS_REPLACE, UserEventType.MESSAGE_FLAGS_SET}:
#         new_flags: int = mask
#         flags: set[VkMessageFlag] = get_flags(new_flags)
#         string = f"Флаги у сообщения: {', '.join(flags_to_human(current_flags=flags))}\n"  # type: ignore
#         flags_cache[event.message_id] = new_flags

#     elif event.type == VkEventType.MESSAGE_FLAGS_RESET:
#         old_flags = get_flags(flags_cache.get(event.message_id, 0))
#         flags = get_flags(mask)
#         diff: set[VkMessageFlag] = flags or set()
#         result_mask: set[VkMessageFlag] = (old_flags - flags) or set()
#         about_removed_flags, about_current_flags = flags_to_human(
#             removed_flags=diff, current_flags=result_mask
#         )
#         string = (
#             f"{', '.join(about_removed_flags)}\n"
#             f"{', '.join(about_current_flags)}\n"
#         )

#     else:
#         raise 

#     save_caches()
#     logger_info(string)
#     string += f'* <a href="{get_message_url(event)}">сообщение</a>'

#     # try:
#     #     await edit_message(
#     #         tg_client=tg_client, string=string, vk_id_=event.message_id, append=True
#     #     )
#     # except KeyError:
#     await send_to_chat(event, tg_client, string, save=False)


async def on_other_event(
    event: Event, api: vkbottle.API, tg_client: telegram_bot.classes.MyTelegram
) -> None:
    from_user = (
        await get_user_name(api, uid)
        if (uid := getattr(event, "from_user"))
        else "*Unknown*"
    )
    in_chat = (
        await get_chat_name(api, uid)
        if (uid := getattr(event, "peer_id"))
        else "*unknown*"
    )

    event_display_name = event.type.name if hasattr(event.type, "name") else event.type

    event_all_args = event.__dict__

    logger_info(
        f"{event_display_name}, {from_user=!r}, {in_chat=!r}, | {event_all_args} | "
    )


flags_human_negatived = {
    VkMessageFlag.UNREAD: "Сообщение прочитано",
    VkMessageFlag.IMPORTANT: "Не помеченное сообщение",
    VkMessageFlag.SPAM: 'Сообщение не помечено как "Спам".',
    VkMessageFlag.DELETED: "Сообщение убрано из корзины",
    VkMessageFlag.DELETED_ALL: "Сообщение не удалено для всех получателей",
}


flags_human = {
    VkMessageFlag.UNREAD: "Сообщение не прочитано",
    VkMessageFlag.OUTBOX: "Исходящее сообщение",
    VkMessageFlag.REPLIED: "На сообщение был создан ответ",
    VkMessageFlag.IMPORTANT: "Помеченное сообщение",
    VkMessageFlag.CHAT: "Сообщение отправлено через чат",
    VkMessageFlag.FRIENDS: "Сообщение отправлено другом",
    VkMessageFlag.DELETED: "Сообщение удалено (в корзине)",
    VkMessageFlag.FIXED: "Сообщение проверено пользователем на спам",
    VkMessageFlag.MEDIA: "Сообщение содержит медиаконтент",
    VkMessageFlag.HIDDEN: "Приветственное сообщение от сообщества",
    VkMessageFlag.SPAM: 'Сообщение помечено как "Спам"',
    VkMessageFlag.DELETED_ALL: "Сообщение удалено для всех получателей",
}


@overload
def flags_to_human(removed_flags: None, current_flags: None) -> None: ...
@overload
def flags_to_human(
    removed_flags: None, current_flags: set[VkMessageFlag | Any]
) -> list[str]: ...
@overload
def flags_to_human(
    removed_flags: set[VkMessageFlag], current_flags: None
) -> list[str]: ...
@overload
def flags_to_human(
    removed_flags: set[VkMessageFlag], current_flags: set[VkMessageFlag]
) -> tuple[list[str], list[str]]: ...
def flags_to_human(
    removed_flags: set[VkMessageFlag] | None = None,
    current_flags: set[VkMessageFlag] | None = None,
) -> tuple[list[str], list[str]] | list[str] | None:
    if removed_flags is None and current_flags is None:
        return None

    result_removed: list[str] | None = None
    result_current: list[str] | None = None

    if removed_flags is not None:
        result_removed = [
            flags_human_negatived.get(flag, f"неизвестное значение {flag}!")
            for flag in (removed_flags or {})
        ]
    if current_flags is not None:
        result_current = [flags_human[flag] for flag in (current_flags or {})]

    if result_removed is not None and result_current is not None:
        return result_removed, result_current
    elif result_removed is not None:
        return result_removed
    elif result_current is not None:
        return result_current
    return None
