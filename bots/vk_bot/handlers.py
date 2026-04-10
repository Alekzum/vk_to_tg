# from utils.my_classes import TgMessage

# from utils.interface.vk_messages import get_tg_id, add_pair

from ..telegram_bot.classes import MyTelegram
from .classes import Message as VkMessage
from pyrogram.types import Message
from pyrogram import errors as pyro_errors
from utils.my_vk_api import VkApiMethod
from utils.my_keyboard import make_button
from .utils import (
    get_pair_for_dict,
    get_tg_id,
    add_pair,
    get_message_url,
    find_first_message_media_url_index,
)
from .my_async_functions import (
    parse_event,
    get_user_name,
    get_chat_name,
    get_dialog_name,
)
from utils.interface import vk_interface
from vk_api.longpoll import Event, VkEventType, VkMessageFlag
from typing import TypedDict, Any, overload, Optional, Literal
import pathlib
import pickle
import pydantic

from pydantic import BaseModel, Field
from utils.my_logging import getLogger

import asyncio


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


# def get_caller() -> FrameType:
#     """module:line"""
#     pre2frame = inspect.currentframe()
#     for _ in range(10):
#         assert pre2frame
#         if pre2frame.f_code.co_name.startswith("logger_"):
#             pre2frame = pre2frame.f_back
#             break
#         pre2frame = pre2frame.f_back

#     assert pre2frame
#     return pre2frame


# def get_extra() -> dict[str, Any]:
#     caller = get_caller()
#     filename = caller.f_code.co_filename
#     funcName = caller.f_code.co_name
#     lineno = caller.f_lineno
#     name = caller.f_code.co_qualname
#     return dict(
#         filename=filename,
#         funcName=funcName,
#         lineno=lineno,
#         name=name,
#     )


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
    caches = Caches(**{i: new_caches.get(i, dict()) for i in caches.copy()})
    globals().update(caches)


def save_caches() -> None:
    caches_file.write_bytes(pickle.dumps(caches))


async def edit_message(
    # event: Event,
    tg_client: MyTelegram,
    string: str,
    vk_id_: Optional[int] = None,
    tg_id_: Optional[int] = None,
    append: bool = False,
) -> None:
    chat_id = tg_client.chat_id
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
        raise ValueError(
            f"Didn't found text at message with id {msg.id}; {msg=}"
        )

    await tg_client.edit_text(
        tg_id, (msg.text.markdown + "\n" + string) if append else string
    )


class ReadData(pydantic.BaseModel):
    peer_id: int
    msg_id: int


async def send_to_chat(
    event: Event,
    tg_client: MyTelegram,
    string: str,
    save: bool = True,
    read_button_data: Optional[ReadData | bool] = None,
    # add_read_button: bool = False,
) -> Message:
    READ_FORMATTER = "read:{peer_id}:{msg_id}"
    chat_id = tg_client.chat_id
    markup = None
    # if add_read_button:
    #     markup = make_button(
    #         "Прочитать", READ_FORMATTER.format(peer_id=getattr(event, "peer_id"), msg_id=event.msg_id)
    #     )
    peer_id = getattr(event, "peer_id", None)
    vk_msg_id = getattr(event, "message_id", None)
    if read_button_data is True:
        if peer_id and vk_msg_id:
            markup = make_button(
                "Прочитать",
                READ_FORMATTER.format(
                    peer_id=peer_id, msg_id=vk_msg_id
                ),
            )
        else:
            logger.warning("didn't get items for button", peer_id=peer_id, vk_msg_id=vk_msg_id)
    elif read_button_data:
        markup = make_button(
            "Прочитать",
            READ_FORMATTER.format(
                peer_id=read_button_data.peer_id, msg_id=read_button_data.msg_id
            ),
        )

    url_idx = find_first_message_media_url_index(string)
    logger.debug("maybe found url index", url_idx=url_idx)

    if vk_msg_id and (
        tg_id := await get_tg_id(chat_id, vk_msg_id)
    ):
        text_info = await tg_client.tg.parser.parse(string)
        old_msg = await tg_client.get_messages(int(tg_id))
        if old_msg.text == text_info["message"]:
            logger.debug("double message! skip")
            return old_msg
        
        msg = await tg_client.reply_text(
            msg_id=int(tg_id),
            text=string,
            reply_markup=markup,
            link_preview_index=url_idx,
        )
    else:
        msg = await tg_client.send_text(
            string, reply_markup=markup, link_preview_index=url_idx
        )

    if not save:
        return msg

    if msg and event.message_id:
        binds_vk_to_tg[event.message_id] = msg.id
        await add_pair(
            msg.id,
            chat_id,
            event.message_id,
            vk_peer_id=getattr(event, "peer_id"),
        )

    elif event.message_id:
        logger.warning("no msg", msg=msg, string=string, event_object=event)
    return msg


async def on_message_edit(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    msg_data = getattr(event, "message_data", {})
    if msg_data and "reaction_id" in msg_data:
        return await on_message_react(event, api, tg_client)

    text, isInBlocklist = await parse_event(event, api)
    if isInBlocklist:
        return

    _previous_message = _full_previous_message = None
    pair_for_dict = get_pair_for_dict(event)
    if pair_for_dict and pair_for_dict in messages_cache:
        _previous_message = messages_cache[pair_for_dict]
        _full_previous_message = full_messages_cache.get(pair_for_dict)

    string = f"[redacted] {text}"
    if pair_for_dict:
        messages_cache[pair_for_dict] = text

    logger.info("Redacted text", text=text)
    logger.debug(
        "Redacted text",
        event_object=event,
        text=text,
        prev_msg=_previous_message,
        full_prev_msg=_full_previous_message,
    )

    await send_to_chat(event, tg_client, string)


async def on_message_new(event: Event, api: VkApiMethod, tg_client: MyTelegram):
    flags_cache[getattr(event, "message_id")] = getattr(event, "flags")

    text, in_block_list = await parse_event(event, api)

    pair_for_dict = get_pair_for_dict(event)
    read_data = None
    if pair_for_dict:
        read_data = ReadData(peer_id=pair_for_dict[0], msg_id=pair_for_dict[1])
        messages_cache[pair_for_dict] = text
        full_messages_cache[pair_for_dict] = event

    if not in_block_list:
        logger.info(text)
        logger.debug(
            "new message",
            event_type=event.type,
            raw_event=(event, event.__dict__),
        )
    else:
        logger.debug(
            "new ignored message",
            event_type=event.type,
            raw_event=(event, event.__dict__),
        )
        return

    if VkMessageFlag.UNREAD in event.message_flags and not event.from_me:
        await send_to_chat(event, tg_client, text, read_button_data=read_data)
    else:
        await send_to_chat(event, tg_client, text)


async def on_real_all_outgoing_messages(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
):
    # chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    chat = await get_dialog_name(api, getattr(event, "peer_id"))
    string = f"Read all outgoing messages in chat {chat}"

    logger.info(string)

    await send_to_chat(event, tg_client, string)


async def on_read_all_incoming_messages(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    logger = getLogger(
        __name__ + ".on_read_incoming", chat_id=tg_client.chat_id
    )
    chat_peer_id = getattr(event, "peer_id")
    chat = await get_dialog_name(api, chat_peer_id)
    string = f"Read all incoming messages in chat {chat}"

    last_read_message: int = getattr(event, "local_id")

    logger.info(
        string,
    )

    await send_to_chat(event, tg_client, string)

    async def inner_iter():
        logger = getLogger(
            __name__ + ".on_read_incoming.iterator", chat_id=tg_client.chat_id
        )

        # somehow get first message with button
        unread_messages = await vk_interface.get_unread_messages(
            tg_client.chat_id
        )
        # messages = await vk_messages.get_last_vk_id(
        #     tg_client.chat_id, as_generator=True
        # )
        key = tg_client.chat_id
        is_iterating = on_read_all_incoming_messages_keys.get(key, False)
        while is_iterating:
            await asyncio.sleep(1)
        try:
            for message in unread_messages:
                # raw_vk_messages = await api.messages.getById(
                #     message_ids=message.vk_id
                # )
                # vk_message = VkMessage.model_validate(
                #     raw_vk_messages["items"][0]
                # )
                if message.vk_peer_id != chat_peer_id:
                    # logger.debug("Skip from not-this chat")
                    continue
                # message.
                elif message.vk_id > last_read_message:
                    # logger.debug("Skip - message is not read")
                    continue
                saved_msg = await vk_interface.get_message_by_vk_id(
                    tg_chat_id=tg_client.chat_id, vk_msg_id=message.vk_id
                )
                if saved_msg is None:
                    logger.debug(
                        "skip empty",
                        tg_id=message.tg_id,
                        vk_msg_id=message.tg_id,
                    )
                    continue
                elif saved_msg.is_read:
                    logger.debug("skip read", tg_id=message.tg_id)
                    continue

                logger.debug("removing markup", tg_id=message.tg_id)
                try:
                    await tg_client.edit_reply_markup(msg_id=message.tg_id)
                except (
                    pyro_errors.MessageNotModified,
                    pyro_errors.MessageIdInvalid,
                ):
                    pass
                await vk_interface.mark_vk_msg_as_read(
                    tg_chat_id=tg_client.chat_id, vk_msg_id=message.vk_id
                )

                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.debug("cancelled")
            on_read_all_incoming_messages_keys[key] = False

    new_task = asyncio.create_task(inner_iter())
    on_read_all_incoming_messages_tasks.append(new_task)
    new_task.add_done_callback(
        lambda _: on_read_all_incoming_messages_tasks.remove(new_task)
    )


on_read_all_incoming_messages_tasks: list[asyncio.Task] = list()
on_read_all_incoming_messages_keys: dict[int, bool] = dict()


async def on_message_react(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    chat = await get_dialog_name(api, getattr(event, "peer_id"))
    # chat = get_from_peer(api, event, conversations_, groups_, profiles_)
    string = f"Read all outgoing messages in chat {chat}"

    logger.info(string)

    await send_to_chat(event, tg_client, string)


async def on_user_typing(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    user_id = getattr(
        event, "user_id", getattr(event, "from_user", getattr(event, "peer_id"))
    )
    from_user = await get_dialog_name(api, user_id)
    # from_user = get_from_user(api, event, profiles_)
    # in_chat = get_in_chat(api, event, conversations_, groups_)

    logger.info(
        "Someone is typing in chat",
        user=from_user,
    )


async def on_user_typing_in_chat(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    user_id = getattr(
        event, "user_id", getattr(event, "from_user", getattr(event, "peer_id"))
    )
    chat_id = (
        (c_id + 2000000000)
        if ((c_id := getattr(event, "chat_id", None)) is not None)
        else getattr(event, "peer_id")
    )  # because it's chat
    from_user = await get_dialog_name(api, user_id)
    in_chat = await get_dialog_name(api, chat_id)
    # from_user = get_from_user(api, event, profiles_)
    # in_chat = get_in_chat(api, event, conversations_, groups_)

    logger.info(
        "Someone is typing in chat",
        user=from_user,
        chat_title=in_chat,
        chat_id=chat_id,
    )


async def on_unread_messages_counter_update(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    global _last_update_string
    # because it's always integer
    unread_messages_count: int = getattr(event, "count")
    string = f"Unread messages count: {unread_messages_count}"
    if _last_update_string != string:
        await tg_client.edit_pinned_text(string)
        _last_update_string = string


def get_flags(mask: int) -> set[VkMessageFlag]:
    return {flag for flag in VkMessageFlag if mask & flag == flag}


def string_flags(flags: set[VkMessageFlag]):
    return ", ".join({i.name for i in flags})


async def on_message_flag_interacted(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    assert event.message_id, (
        "wtf - event with message's flag, but message_id is none"
    )
    # logger.debug(f"{beautify_print(event, need_to_print=False, indent=None)}")

    # chat_id = tg_client.CHAT_ID
    mask = getattr(event, "mask")

    # mask 8 & flag 9 != 9

    if event.type in {
        VkEventType.MESSAGE_FLAGS_REPLACE,
        VkEventType.MESSAGE_FLAGS_SET,
    }:
        new_flags: int = mask
        flags: set[VkMessageFlag] = get_flags(new_flags)
        string = ", ".join(flags_to_human(current_flags=flags)).title() + "\n"
        flags_cache[event.message_id] = new_flags

    elif event.type == VkEventType.MESSAGE_FLAGS_RESET:
        old_flags = get_flags(flags_cache.get(event.message_id, 0))
        flags = get_flags(mask)
        diff: set[VkMessageFlag] = flags or set()
        result_mask: set[VkMessageFlag] = (old_flags - flags) or set()
        about_removed_flags, about_current_flags = flags_to_human(
            removed_flags=diff, current_flags=result_mask
        )
        string = (
            f"{', '.join(about_removed_flags).title()}\n"
            f"{', '.join(about_current_flags).title()}\n"
        )

    else:
        raise

    save_caches()
    logger.info(string)
    string += f'* <a href="{get_message_url(event)}">сообщение</a>'

    # try:
    #     await edit_message(
    #         tg_client=tg_client, string=string, vk_id_=event.message_id, append=True
    #     )
    # except KeyError:
    await send_to_chat(event, tg_client, string, save=False)


async def on_other_event(
    event: Event, api: VkApiMethod, tg_client: MyTelegram
) -> None:
    from_id = (
        await get_user_name(api, uid)
        if not isinstance(uid := getattr(event, "from_id", None), bool)
        and isinstance(uid, int)
        else "*none*"
    )
    in_chat = (
        await get_chat_name(api, uid)
        if (uid := getattr(event, "peer_id"))
        else "*none*"
    )

    # logger.info(
    #     f"{event_display_name}, {from_id=!r}, {in_chat=!r}, | {event_all_args} | "
    # )
    logger.info(
        "Unknown event",
        event_type=event.type,
        from_id=from_id,
        in_chat=in_chat,
        raw_event=event.__dict__,
    )
    # logger.debug("...", event_type=event.type, raw_event=event.__dict__)


def resolve_chat_id(
    peer_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    user_id: Optional[int] = None,
): ...


# flags_human_negatived = {
#     VkMessageFlag.UNREAD: "Сообщение прочитано",
#     VkMessageFlag.IMPORTANT: "Не помеченное сообщение",
#     VkMessageFlag.SPAM: 'Сообщение не помечено как "Спам".',
#     VkMessageFlag.DELETED: "Сообщение убрано из корзины",
#     VkMessageFlag.DELETED_ALL: "Сообщение не удалено для всех получателей",
# }


# flags_human = {
#     VkMessageFlag.UNREAD: "Сообщение не прочитано",
#     VkMessageFlag.OUTBOX: "Исходящее сообщение",
#     VkMessageFlag.REPLIED: "На сообщение был создан ответ",
#     VkMessageFlag.IMPORTANT: "Помеченное сообщение",
#     VkMessageFlag.CHAT: "Сообщение отправлено через чат",
#     VkMessageFlag.FRIENDS: "Сообщение отправлено другом",
#     VkMessageFlag.DELETED: "Сообщение удалено (в корзине)",
#     VkMessageFlag.FIXED: "Сообщение проверено пользователем на спам",
#     VkMessageFlag.MEDIA: "Сообщение содержит медиаконтент",
#     VkMessageFlag.HIDDEN: "Приветственное сообщение от сообщества",
#     VkMessageFlag.SPAM: 'Сообщение помечено как "Спам"',
#     VkMessageFlag.DELETED_ALL: "Сообщение удалено для всех получателей",
# }


flags_human_negatived = {
    VkMessageFlag.UNREAD: "Прочитано",
    VkMessageFlag.IMPORTANT: "Не помечено",
    VkMessageFlag.SPAM: 'Не помечено как "Спам".',
    VkMessageFlag.DELETED: "Убрано из корзины",
    VkMessageFlag.DELETED_ALL: "Не удалено для всех получателей",
}


flags_human = {
    VkMessageFlag.UNREAD: "Не прочитано",
    VkMessageFlag.OUTBOX: "Исходящее",
    VkMessageFlag.REPLIED: "На сообщение был создан ответ",
    VkMessageFlag.IMPORTANT: "Помечен",
    VkMessageFlag.CHAT: "Отправлено через чат",
    VkMessageFlag.FRIENDS: "Отправлено другом",
    VkMessageFlag.DELETED: "Удалено (в корзине)",
    VkMessageFlag.FIXED: "Проверено пользователем на спам",
    VkMessageFlag.MEDIA: "Содержит медиаконтент",
    VkMessageFlag.HIDDEN: "Приветственное сообщение от сообщества",
    VkMessageFlag.SPAM: 'Помечено как "Спам"',
    VkMessageFlag.DELETED_ALL: "Удалено для всех получателей",
}


@overload
def flags_to_human(removed_flags: set[VkMessageFlag]) -> list[str]: ...
@overload
def flags_to_human(*, current_flags: set[VkMessageFlag]) -> list[str]: ...
@overload
def flags_to_human(
    removed_flags: set[VkMessageFlag], current_flags: set[VkMessageFlag]
) -> tuple[list[str], list[str]]: ...
@overload
def flags_to_human(
    removed_flags: Literal[None], current_flags: set[VkMessageFlag]
) -> list[str]: ...
@overload
def flags_to_human(
    removed_flags: set[VkMessageFlag], current_flags: Literal[None]
) -> list[str]: ...
@overload
def flags_to_human(
    removed_flags: None = None, current_flags: None = None
) -> None: ...
def flags_to_human(
    removed_flags: Optional[set[VkMessageFlag]] = None,
    current_flags: Optional[set[VkMessageFlag]] = None,
) -> tuple[list[str], list[str]] | list[str] | None:
    if removed_flags is None and current_flags is None:
        return None

    result_removed: Optional[list[str]] = None
    result_current: Optional[list[str]] = None

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
