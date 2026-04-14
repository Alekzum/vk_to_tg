from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.kbd import (
    Back,
    Cancel,
    Button,
    Select,
    ScrollingGroup,
    SwitchTo,
)
from aiogram_dialog.api.entities import ChatEvent
from aiogram_dialog.widgets.common import ManagedScroll

# from ...vk_bot.my_async_functions import (
#     # get_dialog_name,
#     # Message as VkMessage,
#     # get_text_message,
# )
from ...vk_bot.my_async_functions import get_dialog_name, parse_message
from ...vk_bot.classes import Message as VkMessage
from ...vk_bot.classes.get_conversations import GetConversations
from ..utils.my_vk import get_vk_api, VkApiMethod, upload_photo
from ..utils.fsm_states import BotStates
from .handler_vk import CHATS_PAGE_LEN, maybe_inputs
from typing import Any
import operator
from utils.my_logging import getLogger
import asyncio
from io import BytesIO

logger = getLogger(__name__)
rt = Router(name=__name__)


async def get_start_data(event: ChatEvent, dialog_manager: DialogManager):
    start_data = dialog_manager.start_data
    if not isinstance(start_data, dict):
        logger.warning("Start data invalid!", start_data_type=type(start_data))
        return
    dialog_manager.dialog_data.update(start_data)


async def on_send_message(dialog_manager: DialogManager, **kwargs) -> dict[str, str]:
    user = dialog_manager.event.from_user
    if not user:
        logger.error("Didn't found user!")
        return dict(msg_text="*НЕИЗВЕСТНО*", msg_chat="*НЕИЗВЕСТНО*")

    api = await get_vk_api(user.id)
    # print("dialog_data", dialog_manager_dialog_data=dialog_manager.dialog_data)
    photo = dialog_manager.dialog_data.get("msg_photo", None)
    text = dialog_manager.dialog_data["msg_text"]
    chat_name = dialog_manager.dialog_data["msg_name"]
    result = dict(msg_text=text, msg_chat=chat_name)

    if photo:
        result["msg_photo"] = photo

    reply_message = dialog_manager.dialog_data.get("msg_to", None)
    if not reply_message:
        return result

    rtm = await api.messages.getById(message_ids=reply_message)
    rtm_vk = VkMessage(**rtm["items"][0])
    message_text = (await parse_message(rtm_vk, api, 0))[0]
    result["msg_message"] = message_text
    return result


# Chats: confirm


# # Confirm answer
# async def choose_chat_confirm(
#     callback: CallbackQuery, button: Button, dialog_manager: DialogManager
# ):
#     await callback.answer()
#     await dialog_manager.switch_to(BotStates.Answer.CHOOSE_CHAT)


# # Decline answer
# async def choose_chat_cancel(
#     callback: CallbackQuery, button: Button, dialog_manager: DialogManager
# ):
#     clear_reply_data(dialog_manager)
#     await callback.answer("Ладно")


# Confirm answer
async def send_confirm(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    dialog_data = dialog_manager.dialog_data
    action = dialog_data["msg_act"]
    content_type = dialog_data["msg_type"]

    msg_vk_id = dialog_data["msg_to"]
    chat_vk_id = dialog_data["msg_in"]

    tg_user_id = callback.from_user.id
    api = await get_vk_api(tg_user_id)

    send_kwargs: dict[str, str | int] = dict()
    if action == "reply":
        if msg_vk_id is None:
            return await callback.answer("Я не знаю такое сообщение.")
        raw_msg = (await api.messages.getById(message_ids=msg_vk_id))["items"][0]
        vk_msg = VkMessage(**raw_msg)

        send_kwargs.update(
            dict(
                peer_id=vk_msg.peer_id,
                random_id=vk_msg.random_id or 0,
                reply_to=vk_msg.id,
                # message=msg_text,
            )
        )

    else:
        if chat_vk_id is None:
            return await callback.answer("Я не знаю такой чат.")
        send_kwargs.update(
            dict(
                peer_id=chat_vk_id,
                random_id=0,
            )
        )

    match content_type:
        case "text":
            text = dialog_data["msg_text"]
            send_kwargs["message"] = text

        case "photo":
            if not callback.bot:
                raise RuntimeError
            text = dialog_data["msg_text"]
            raw_photos: set[str] | str = dialog_data["msg_photo"]
            photos = raw_photos if isinstance(raw_photos, set) else {raw_photos}
            attachments = []
            for photo in photos:
                b_io = BytesIO()

                photo_ = await callback.bot.download(photo, destination=b_io)
                if not photo_:
                    raise RuntimeError
                photo_id = await upload_photo(photo=b_io, tg_user_id=tg_user_id)
                attachments.append(photo_id)

            send_kwargs.update(dict(attachment=",".join(attachments), message=text))

        case _:
            raise NotImplementedError

    out_msg = await api.messages.send(**send_kwargs)

    clear_reply_data(dialog_manager)
    return dict(message=f"Отправлено сообщение: {out_msg}")


# Decline answer
async def send_cancel(
    callback: CallbackQuery, button: Button, dialog_manager: DialogManager
):
    clear_reply_data(dialog_manager)
    await callback.answer("Ладно")


# Select chat
async def on_chat_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: int,
):
    user_id = callback.from_user.id
    # logger.debug("selected chat", user_id=user_id, item_id=item_id)
    chats_list = dialog_manager.dialog_data["vk_chat_list_data"]
    chats_dict: dict[int, tuple[str, int]] = {p[0]: (p[1], p[2]) for p in chats_list}
    selected_chat = chats_dict[item_id]
    logger.debug(
        "selected chat",
        user_id=user_id,
        item_id=item_id,
        selected_chat=selected_chat,
    )

    selected_chat_id = selected_chat[1]
    selected_chat_name = selected_chat[0]

    dialog_manager.dialog_data["msg_in"] = selected_chat_id
    dialog_manager.dialog_data["msg_name"] = selected_chat_name
    dialog_manager.dialog_data["msg_to"] = None
    await dialog_manager.switch_to(BotStates.Answer.SEND_MESSAGE)


async def async_parse_chats(
    api: VkApiMethod,
    raw_chats: GetConversations,
    offset: int,
    count: int = CHATS_PAGE_LEN,
) -> list[tuple[int, str, int]]:
    """list of (chat_index, chat_name, chat_peer_id)"""

    # we get only CHATS_PAGE_LEN chat with offset current_page*CHATS_PAGE_LEN
    peers_to_find: list[tuple[str, int]] = []
    async with asyncio.TaskGroup() as group:
        for chat in raw_chats.response.items:
            peer_id = chat.conversation.peer.id
            peer_type = chat.conversation.peer.type
            task = group.create_task(
                get_dialog_name(dialog_id=peer_id, api=api, dialog_type=peer_type)
            )
            task.add_done_callback(
                (
                    lambda peer_id_: (
                        lambda f: peers_to_find.append((f.result(), peer_id_))
                    )
                )(peer_id)
            )
    peers: list[tuple[str, int]] = (
        []
        + [("_", -0)] * offset
        + peers_to_find
        + [("_", -0)] * (raw_chats.response.count - (offset + count))
    )
    # [:offset], [offset:offset+count], [offset+count:]
    #  offset     count                  items-(offset+count)

    chats_list: list[tuple[int, str, int]] = [
        (index, item[0], item[1]) for (index, item) in enumerate(peers)
    ]

    return chats_list


async def parse_chats(
    api, raw_chats: GetConversations, offset: int, count: int = CHATS_PAGE_LEN
) -> list[tuple[int, str, int]]:
    """list of (chat_index, chat_name, chat_peer_id)"""

    # we get only CHATS_PAGE_LEN chat with offset current_page*CHATS_PAGE_LEN
    raw_peers = [chat.conversation.peer.id for chat in raw_chats.response.items]
    peers_to_find: list[tuple[str, int]] = [
        (await get_dialog_name(api, peer_id), peer_id) for peer_id in raw_peers
    ]
    peers: list[tuple[str, int]] = (
        []
        + [("_", -0)] * offset
        + peers_to_find
        + [("_", -0)] * (raw_chats.response.count - (offset + count))
    )
    # [:offset], [offset:offset+count], [offset+count:]
    #  offset     count                  items-(offset+count)

    chats_list: list[tuple[int, str, int]] = [
        (index, item[0], item[1]) for (index, item) in enumerate(peers)
    ]

    return chats_list


async def on_choose_blacklist(
    dialog_manager: DialogManager, **data
) -> dict[str, list[tuple[int, str, int]]]:
    """{"chats": (chat_index, chat_name, chat_peer_id)}"""
    if not (user := dialog_manager.event.from_user):
        dialog_manager.dialog_data["vk_chat_list_data"] = list()
        return {"chats": []}

    offset = dialog_manager.dialog_data.get("vk_chat_list_offset", 0)
    raw_chats_: dict = dialog_manager.dialog_data.get("vk_chat_conversations", {})

    dialog_manager.dialog_data["vk_chat_conversations"] = raw_chats_
    raw_chats = raw_chats_.get(offset, None)

    user_id = user.id
    api = await get_vk_api(user_id)

    if not raw_chats:
        logger.debug("get chats", user_id=user_id)
        response = await api.messages.getConversations(
            offset=offset, count=CHATS_PAGE_LEN
        )
        raw_chats = GetConversations(response=response)
        dialog_manager.dialog_data["vk_chat_conversations"][offset] = raw_chats

    dialog_manager.dialog_data["vk_chat_list_offset"] = offset

    chats_list = await async_parse_chats(api, raw_chats, offset)

    dialog_manager.dialog_data["vk_chat_list_data"] = chats_list
    logger.debug("return chats", user_id=user_id, chats_list_len=len(chats_list))
    return {"chats": chats_list}


async def on_page_changed(
    event: ChatEvent, widget: ManagedScroll, dialog_manager: DialogManager
):
    page = await widget.get_page()
    dialog_manager.dialog_data["vk_chat_list_offset"] = page * CHATS_PAGE_LEN


def clear_reply_data(dialog_manager: DialogManager):
    for key in [
        "msg_act",
        "msg_type",
        "msg_text",
        "msg_photo",
        "msg_text",
        "msg_to",
        "msg_name",
        "msg_in",
        "vk_chat_list",
        "vk_chat_list_data",
        "vk_chat_list_offset",
        "vk_chat_conversations",
    ]:
        dialog_manager.dialog_data.pop(key, None)


send_message_dialog = Dialog(
    Window(
        Multi(
            Format(
                "Отправить сообщение с вашим изображением? "
                "Ваши фото: {msg_photo}\n"
                "Ваше описание к фото:<blockquote expandable>{msg_text}</blockquote>\n\n"
                "Чат, в котором вы хотите отправить ответ: {msg_chat}",
                when=F["msg_photo"],
            ),
            Format(
                "Отправить сообщение с вашим текстом? "
                "Ваш текст:<blockquote expandable>{msg_text}</blockquote>\n\n"
                "Чат, в котором вы хотите отправить ответ: {msg_chat}",
                when=~F["msg_photo"],
            ),
            Format("С ответом на сообщение: {msg_message}", when="msg_message"),
        ),
        *maybe_inputs,
        Cancel(
            id="vk_send_cancel",
            text=Const("Нет"),
            on_click=send_cancel,
            # state=BotStates.START_POLLING,
        ),
        Cancel(
            id="vk_send_confirm",
            text=Const("Да"),
            on_click=send_confirm,
            # state=BotStates.START_POLLING,
        ),
        state=BotStates.Answer.SEND_MESSAGE,
        getter=on_send_message,
    ),
    Window(
        Const("Выберите чат, в котором вы хотите написать ответ"),
        ScrollingGroup(
            Select(
                Format("{item[1]}"),
                id="vk_send_chat_select",
                item_id_getter=operator.itemgetter(0),
                items="chats",
                type_factory=int,
                on_click=on_chat_selected,
            ),
            id="vk_send_chat_list",
            width=1,
            height=CHATS_PAGE_LEN,
            on_page_changed=on_page_changed,
        ),
        Cancel(
            text=Const("Отмена"),
            id="vk_send_chat_cancel",
            on_click=send_cancel,
            # state=BotStates.START_POLLING,
        ),
        state=BotStates.Answer.CHOOSE_CHAT,
        getter=on_choose_blacklist,
        preview_add_transitions=[Back()],
    ),
    Window(
        Const("Вы хотите посмотреть чаты, в которых можете отправить ответ?"),
        SwitchTo(
            id="vk_choose_chat_confirm",
            text=Const("Да"),
            # on_click=choose_chat_confirm,
            state=BotStates.Answer.CHOOSE_CHAT,
        ),
        Cancel(
            id="vk_choose_chat_cancel",
            text=Const("Нет"),
            # on_click=choose_chat_cancel,
            # state=BotStates.START_POLLING,
        ),
        state=BotStates.Answer.MAYBE_CHOOSE_CHAT,
    ),
    on_start=get_start_data,
    # on_close=clear_reply_data
)

# settings_dialog = Dialog(Window(state=SettingStates.MENU))


rt.include_router(send_message_dialog)
