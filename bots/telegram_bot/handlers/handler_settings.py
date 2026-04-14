import re
from typing import Any

from aiogram import F, Router, types

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
from aiogram_dialog.widgets.input import TextInput, ManagedTextInput

from aiogram_dialog.api.entities import ChatEvent, MarkupVariant
from utils.config import Config
from utils.my_vk_api import AsyncVkApi
from utils.interface.user_settings import UserSettingsManager
from ..utils.fsm_states import SettingStates
from .handler_vk_send import (
    on_choose_blacklist,
    CHATS_PAGE_LEN,
    on_page_changed,
)

import operator
from utils.my_logging import getLogger


# region blacklist
class BlacklistThings:
    @staticmethod
    async def get_chats_blacklist(dialog_manager: DialogManager, **data):
        if not (user := dialog_manager.event.from_user):
            logger.warning("Didn't found user_id!")
            return dict(chats_blacklist="*НЕИЗВЕСТНО*")

        logger.debug("get user's blacklist", user_id=user.id)
        cfg = await Config(user.id).load_values()
        blacklist = ", ".join([str(i) for i in cfg.blacklist])

        return dict(chats_blacklist=blacklist)

    @staticmethod
    async def on_selected_blacklist(dialog_manager: DialogManager, **data):
        if not (user := dialog_manager.event.from_user):
            logger.warning("Didn't found user_id!")
            return dict(chats_blacklist="*НЕИЗВЕСТНО*")

        logger.debug("get user's selected blacklist", user_id=user.id)
        cfg = await Config.load_user_values(user.id)
        peer_ids = cfg.blacklist
        blacklist = (
            ", ".join([str(i) for i in peer_ids]) or "*Чёрный список пуст*"
        )

        return dict(chats_blacklist=blacklist)

    @staticmethod
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

        await UserSettingsManager(user_id).blacklist.set(peer_ids)

    @staticmethod
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


# region api key
class AccessTokenThings:
    re_access_token = re.compile(r"^vk1\.a\.[A-Za-z0-9-]{215}$")

    @staticmethod
    def str_access_token(raw_value: Any) -> Any:
        value = str(raw_value)
        if AccessTokenThings.re_access_token.match(value) is None:
            raise ValueError(
                "Value didn't matched access token's regular expression",
                value,
                AccessTokenThings.re_access_token,
            )
        return value

    @staticmethod
    async def on_write_token(dialog_manager: DialogManager, **data):
        if not (user := dialog_manager.event.from_user):
            logger.warning("Didn't found user_id!")
            return dict(access_token="Неизвестен")
        saved_user = await UserSettingsManager(user.id).user.get()

        return dict(access_token=saved_user.vk_token)

    @staticmethod
    async def save_access_token(
        event: types.CallbackQuery,
        widget: Button,
        dialog_manager: DialogManager,
        # selected_id: int,
    ):
        if not (user := event.from_user):
            await event.answer("Вы как-то обошли написание токена")
            return logger.warning("Didn't found user_id!")

        user_id = user.id
        logger.debug("saving blacklist for user", user_id=user_id)

        new_access_token = dialog_manager.dialog_data.get(
            "vk_new_access_token", None
        )
        if new_access_token is None:
            return logger.warning("Didn't found user_id!")

        await UserSettingsManager(user_id).token.set(vk_token=new_access_token)

    @staticmethod
    async def correct_access_token(
        message: types.Message,
        widget: ManagedTextInput[str],
        dialog_manager: DialogManager,
        data: str,
    ):
        await message.answer("Получен API-ключ, проверка...")
        vk_api = AsyncVkApi(token=data)
        try:
            user = (await vk_api.get_api().users.get(name_case="gen"))[0]
        except Exception as ex:
            await message.answer(f"Поймана ошибка при проверке: {ex}.")
            logger.warning("Didn't logged in", exc_info=True)
            return
        full_name = " ".join(
            (
                *(
                    x
                    for x in (user.get("last_name"), user.get("first_name"))
                    if x
                ),
                (f"({user['id']})"),
            )
        )
        await message.answer(
            f"API-ключ валиден, выполнен вход от имени {full_name}"
        )
        dialog_manager.dialog_data["vk_new_access_token"] = data
        await dialog_manager.next()

    @staticmethod
    async def wrong_access_token(
        message: types.Message,
        widget: ManagedTextInput[str],
        dialog_manager: DialogManager,
        error: ValueError,
    ):
        await message.answer(
            "Введённое вами значение не похоже на access_token (vk1.a...)"
        )

    @staticmethod
    async def render_markup(
        data: dict,
        manager: DialogManager,
        keyboard: list[list[types.InlineKeyboardButton | types.KeyboardButton]]
        | list[list[types.KeyboardButton]],
    ) -> MarkupVariant:
        token = data["access_token"]
        button = types.InlineKeyboardButton(
            text="Cкопировать токен",
            copy_text=types.CopyTextButton(text=token),
        )
        return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


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
        Start(
            Const("Изменить/Получить сохранённый API-ключ"),
            id="vk_apikey_start",
            state=SettingStates.ApiKey.SELECT,
        ),
        Cancel(Const("Назад")),
        state=SettingStates.MENU,
        getter=BlacklistThings.get_chats_blacklist,
    )
)

access_token_dialog = Dialog(
    Window(
        # Format("Сохранённый токен: <tg-spoiler>{access_token}</tg-spoiler>"),
        Const(
            "Скопируйте текущий токен или введите новый (можно получить с помощью https://vkhost.github.io/)"
        ),
        TextInput(
            "vk_apikey_input",
            type_factory=AccessTokenThings.str_access_token,
            filter=F.text.regexp(AccessTokenThings.re_access_token),
            on_success=AccessTokenThings.correct_access_token,
            on_error=AccessTokenThings.wrong_access_token,
        ),
        # ScrollingGroup(
        #     Multiselect(
        #         checked_text=Format("• {item[1]}"),
        #         unchecked_text=Format("{item[1]}"),
        #         id="vk_blacklist_chats_item",
        #         item_id_getter=operator.itemgetter(0),
        #         items="chats",
        #         type_factory=int,
        #         on_state_changed=check_blacklist,
        #         # on_click=check_blacklist
        #     ),
        #     id="vk_blacklist_chats",
        #     width=1,
        #     height=CHATS_PAGE_LEN,
        #     on_page_changed=on_page_changed,
        # ),
        # Next(Const("Сохранить")),
        Cancel(Const("Отмена")),
        getter=AccessTokenThings.on_write_token,
        state=SettingStates.ApiKey.SELECT,
        markup_factory=AccessTokenThings,
    ),
    Window(
        Format(
            "Ваш будущий ключ: {dialog_data['vk_new_access_token']}. Хотите сохранить ключ?"
        ),
        Cancel(Const("Да"), on_click=AccessTokenThings.save_access_token),
        Back(Const("Нет")),
        state=SettingStates.ApiKey.CONFIRM,
    ),
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
                on_state_changed=BlacklistThings.check_blacklist,
                # on_click=check_blacklist
            ),
            id="vk_blacklist_chats",
            width=1,
            height=CHATS_PAGE_LEN,
            on_page_changed=on_page_changed,
        ),
        Next(Const("Сохранить")),
        Cancel(Const("Отмена")),
        getter=on_choose_blacklist,
        state=SettingStates.Blacklist.SELECT,
    ),
    Window(
        Format(
            "Ваш выбор чатов: {chats_blacklist}. Хотите сохранить чёрный список?"
        ),
        Cancel(Const("Да"), on_click=BlacklistThings.save_blacklist),
        Back(Const("Нет")),
        state=SettingStates.Blacklist.CONFIRM,
        getter=BlacklistThings.on_selected_blacklist,
    ),
)


rt.include_routers(common_dialog, blacklist_dialog, access_token_dialog)
