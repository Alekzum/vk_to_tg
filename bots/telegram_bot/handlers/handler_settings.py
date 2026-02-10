from aiogram import Router

# from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.kbd import (
    Button,
    Cancel,
    Next,
    Back,
    Start,
    Multiselect,
    ScrollingGroup,
    ManagedMultiselect,
)

from aiogram_dialog.api.entities import ChatEvent
from utils.config import Config
from utils.interface.user_settings import set_blacklist
from ..utils.fsm_states import SettingStates
from .handler_vk_send import on_choose_chat, CHATS_PAGE_LEN, on_page_changed

import operator
from utils.my_logging import getLogger


async def get_chats_blacklist(dialog_manager: DialogManager, **data):
    if not (user := dialog_manager.event.from_user):
        logger.warning("Didn't found user_id!")
        return dict(chats_blacklist="*НЕИЗВЕСТНО*")

    logger.debug("get user's blacklist", user_id=user.id)
    cfg = await Config(user.id).load_values()
    blacklist = ", ".join([str(i) for i in cfg._blacklist])

    return dict(chats_blacklist=blacklist)


async def get_selected_blacklist(dialog_manager: DialogManager, **data):
    if not (user := dialog_manager.event.from_user):
        logger.warning("Didn't found user_id!")
        return dict(chats_blacklist="*НЕИЗВЕСТНО*")

    logger.debug("get user's selected blacklist", user_id=user.id)
    # cfg = await Config(user.id).load_values()
    peer_ids = dialog_manager.dialog_data.get("vk_blacklist_peer_ids", [])
    blacklist = ", ".join([str(i) for i in peer_ids]) or "*Чёрный список пуст*"

    return dict(chats_blacklist=blacklist)


async def save_blacklist(
    event: ChatEvent,
    widget: Button,
    dialog_manager: DialogManager,
    # selected_id: int,
):
    if not (user := event.from_user):
        return logger.warning("Didn't found user_id!")

    user_id = user.id
    logger.debug("saving blacklist for user", user_id=user_id)

    peer_ids = dialog_manager.dialog_data.get("vk_blacklist_peer_ids", [])

    await set_blacklist(user_id, peer_ids)


async def check_blacklist(
    event: ChatEvent,
    widget: ManagedMultiselect,
    dialog_manager: DialogManager,
    selected_id: int,
):
    if not (user := event.from_user):
        return logger.warning("Didn't found user_id!")
    user_id = user.id
    logger.debug("selected ids for user", user_id=user_id)

    chats_data: list[tuple[int, str, int]] = dialog_manager.dialog_data[
        "vk_chat_list_data"
    ]
    chats_data = list(chats_data)
    item_ids = widget.get_checked()

    peer_ids = []
    for item in chats_data:
        if item[0] in item_ids:
            peer_ids.extend([item[1], item[2]])

    logger.debug(
        "new blacklist for user",
        selected_item_ids=item_ids,
        peer_ids=peer_ids,
        user_id=user_id,
    )
    dialog_manager.dialog_data["vk_blacklist_peer_ids"] = peer_ids


rt = Router(name=__name__)
logger = getLogger(__name__)


common_dialog = Dialog(
    Window(
        Format("Ваш чёрный список: {chats_blacklist}"),
        Start(
            Const("Изменить чёрный список"),
            id="vk_blacklist_start",
            state=SettingStates.Blacklist.SELECT,
        ),
        Cancel(Const("Назад")),
        state=SettingStates.MENU,
        getter=get_chats_blacklist,
    )
)

blacklist_dialog = Dialog(
    Window(
        Const("Выбирайте чаты, которые хотите добавить в чёрный список"),
        ScrollingGroup(
            Multiselect(
                checked_text=Format("• {item[1]}"),
                unchecked_text=Format("{item[1]}"),
                id="vk_blacklist_chats_item",
                item_id_getter=operator.itemgetter(0),
                items="chats",
                type_factory=int,
                on_state_changed=check_blacklist,
                # on_click=check_blacklist
            ),
            id="vk_blacklist_chats",
            width=1,
            height=CHATS_PAGE_LEN,
            on_page_changed=on_page_changed,
        ),
        Next(Const("Сохранить")),
        Cancel(Const("Отмена")),
        getter=on_choose_chat,
        state=SettingStates.Blacklist.SELECT,
    ),
    Window(
        Format(
            "Ваш выбор чатов: {chats_blacklist}. Хотите сохранить чёрный список?"
        ),
        Cancel(Const("Да"), on_click=save_blacklist),
        Back(Const("Нет")),
        state=SettingStates.Blacklist.CONFIRM,
        getter=get_selected_blacklist,
    ),
)


rt.include_routers(common_dialog, blacklist_dialog)
