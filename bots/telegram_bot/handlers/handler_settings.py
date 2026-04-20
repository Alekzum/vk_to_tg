import re
from typing import Any, cast

from aiogram import Router, types

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
from bots.telegram_bot.utils.my_vk_classes import VKApi, get_vk_api
from utils.config import Config
from utils.my_vk_api import AsyncVkApi
from utils.interface.user_settings import UserSettingsManager
from ..utils.fsm_states import TGSettingStates
from .handler_vk_send import (
    CHATS_PAGE_LEN,
    chats_getter,
    on_page_changed,
)

import operator
from utils.my_logging import getLogger


from inspect import iscoroutinefunction
import vk_api
from ...vk_bot.classes.get_conversations import GetConversations


# region blacklist
class BlacklistThings:
    @staticmethod
    async def chats_getter(manager: DialogManager, **data):
        user: types.User = manager.middleware_data["user"]

        logger.debug("get user's blacklist", user_id=user.id)
        cfg = await Config(user.id).load_values()
        blacklist = ", ".join([str(i) for i in cfg.blacklist])

        return dict(chats_blacklist=blacklist)

    @staticmethod
    async def on_selected_blacklist(manager: DialogManager, **data):
        user: types.User = manager.middleware_data["user"]

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
        manager: DialogManager,
        # selected_id: int,
    ):
        user: types.User = manager.middleware_data["user"]

        user_id = user.id
        logger.debug("saving blacklist for user", user_id=user_id)

        peer_ids = manager.dialog_data.get("vk_blacklist_peer_ids", [])

        await UserSettingsManager(user_id).blacklist.set(peer_ids)

    @staticmethod
    async def on_check_blacklist_click(
        event: types.CallbackQuery,
        select: ManagedMultiselect[int],
        manager: DialogManager,
        data: int,
    ) -> None:
        user: types.User = event.from_user

        user_id = user.id
        logger.debug("selected ids for user", user_id=user_id)

        chats_data: list[tuple[int, str, int]] = manager.dialog_data[
            "vk_chat_list_data"
        ]
        chats_data = list(chats_data)
        item_ids = select.get_checked()

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
        manager.dialog_data["vk_blacklist_peer_ids"] = peer_ids

    @staticmethod
    async def parse_chats(
        api: VKApi,
        raw_chats: GetConversations,
        offset: int,
        count: int = CHATS_PAGE_LEN,
    ) -> list[tuple[int, str, int]]:
        """list of (chat_index, chat_name, chat_peer_id)"""

        # we get only CHATS_PAGE_LEN chat with offset current_page*CHATS_PAGE_LEN
        raw_peers = [
            chat.conversation.peer.id for chat in raw_chats.response.items
        ]
        peers_to_find: list[tuple[str, int]] = [
            (await api.get_peer(peer_id), peer_id) for peer_id in raw_peers
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

    @staticmethod
    async def check_blacklist_access(
        cb: types.CallbackQuery, button: Button, manager: DialogManager
    ) -> None:
        """{"chats": (chat_index, chat_name, chat_peer_id)}"""
        user: types.User = cb.from_user

        offset = manager.dialog_data.get("vk_chat_list_offset", 0)
        raw_chats_: dict = manager.dialog_data.get("vk_chat_conversations", {})

        manager.dialog_data["vk_chat_conversations"] = raw_chats_
        raw_chats = raw_chats_.get(offset, None)

        user_id = user.id
        api = await get_vk_api(user_id)

        if not raw_chats:
            logger.debug("get chats", user_id=user_id)
            try:
                response = await api.api.get_api().messages.getConversations(
                    offset=offset, count=CHATS_PAGE_LEN
                )
            except vk_api.ApiError as ex:
                logger.warning(
                    "Didn't got chats bc exception",
                    user_id=user_id,
                    exc_info=True,
                )

                answer = getattr(manager.event, "answer")
                if iscoroutinefunction(answer):
                    await answer(f"Failed! {ex}")
                await manager.answer_callback()

                return None
            raw_chats = GetConversations(response=response)
            manager.dialog_data["vk_chat_conversations"][offset] = raw_chats

        manager.dialog_data["vk_chat_list_offset"] = offset

        chats_list = await BlacklistThings.parse_chats(api, raw_chats, offset)

        manager.dialog_data["vk_chat_list_data"] = chats_list
        logger.debug(
            "return chats", user_id=user_id, chats_list_len=len(chats_list)
        )
        await manager.start(
            TGSettingStates.Blacklist.SELECT, data={"chats": chats_list}
        )


# region api key
class AccessTokenThings:
    VK_KEY_NAME = "vk_new_access_token"
    re_access_token = re.compile(r"^vk1\.a\.[A-Za-z0-9\-\_]+$")

    @staticmethod
    def str_access_token(raw_value: Any) -> Any:
        value = str(raw_value)
        if AccessTokenThings.re_access_token.match(value) is None:
            raise ValueError(
                "Value didn't matched access token's regular expression",
                AccessTokenThings.re_access_token,
                value,
            )
        return value

    @staticmethod
    async def on_write_token(manager: DialogManager, **data):
        logger.debug("Getting user's ID")
        event = manager.event
        unknown_data = "Неизвестно"
        if isinstance(event, types.ErrorEvent):
            logger.warning("Got error event", event_caused=manager.event)
            return {AccessTokenThings.VK_KEY_NAME: unknown_data}
        elif event.from_user is None:
            logger.warning(
                "Got message sent to channel", event_caused=manager.event
            )
            return {AccessTokenThings.VK_KEY_NAME: unknown_data}

        user_id = event.from_user.id
        logger.debug("Getting token", user_id=user_id)

        data = await UserSettingsManager(user_id).token.get()
        if data is None:
            logger.warning(
                "Got unknown token",
                event_caused=manager.event,
                user_id=user_id,
            )
            data = unknown_data
        manager.dialog_data[AccessTokenThings.VK_KEY_NAME] = data
        manager.middleware_data["user_id"] = user_id
        return {AccessTokenThings.VK_KEY_NAME: data}

    @staticmethod
    async def remove_access_token(
        event: types.CallbackQuery,
        widget: Button,
        manager: DialogManager,
        # selected_id: int,
    ):
        user: types.User = event.from_user
        manager.middleware_data["user"] = user

        token = await UserSettingsManager(user.id).token.get()
        manager.dialog_data.setdefault(AccessTokenThings.VK_KEY_NAME, token)

    @staticmethod
    async def save_access_token(
        event: types.CallbackQuery,
        widget: Button,
        manager: DialogManager,
        # selected_id: int,
    ):
        user: types.User = event.from_user
        manager.middleware_data["user"] = user

        logger.debug("saving blacklist for user", user_id=user.id)

        new_access_token = manager.dialog_data.get(
            AccessTokenThings.VK_KEY_NAME, None
        )
        if new_access_token is None:
            return logger.warning("Didn't found user_id!")

        await UserSettingsManager(user.id).token.set(vk_token=new_access_token)

    @staticmethod
    async def correct_access_token(
        message: types.Message,
        widget: ManagedTextInput[str],
        manager: DialogManager,
        data: str,
    ):
        await message.delete()
        log_msg = await message.answer("Получен API-токен, проверка...")
        vk_api = AsyncVkApi(token=data)
        try:
            vk_user = (await vk_api.get_api().users.get(name_case="gen"))[0]
        except Exception as ex:
            await log_msg.reply(f"Поймана ошибка при проверке: {ex}.")
            logger.warning("Didn't logged in", exc_info=True)
            return
        full_name = " ".join(
            (
                *(
                    x
                    for x in (
                        vk_user.get("last_name"),
                        vk_user.get("first_name"),
                    )
                    if x
                ),
                (f"({vk_user['id']})"),
            )
        )
        await log_msg.reply(
            f"API-токен валиден, выполнен вход от имени {full_name}"
        )
        manager.dialog_data[AccessTokenThings.VK_KEY_NAME] = data
        await manager.next()

    @staticmethod
    async def wrong_access_token(
        message: types.Message,
        widget: ManagedTextInput[str],
        manager: DialogManager,
        error: ValueError,
    ):
        user: types.User = manager.middleware_data["user"]

        logger.debug(
            "got wrong token",
            from_user=user.full_name,
            from_id=user.id,
            error=error,
        )
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
        user: types.User = manager.middleware_data["user"]
        kbd = cast(list[list[types.InlineKeyboardButton]], keyboard)

        token = await UserSettingsManager(user.id).token.get() or "Неизвестно"
        button = types.InlineKeyboardButton(
            text="Cкопировать токен",
            copy_text=types.CopyTextButton(text=token),
        )
        kbd.append([button])
        return types.InlineKeyboardMarkup(inline_keyboard=kbd)


rt = Router(name=__name__)
logger = getLogger(__name__)


common_dialog = Dialog(
    Window(
        Format("Ваш чёрный список: {chats_blacklist}"),
        Start(
            Const("Изменить чёрный список"),
            id="vk_blacklist_start",
            state=TGSettingStates.Blacklist.SELECT,
            on_click=BlacklistThings.check_blacklist_access,
        ),
        Start(
            Const("Изменить/Получить сохранённый API-токен"),
            id="vk_apikey_start",
            state=TGSettingStates.ApiKey.SELECT,
        ),
        Cancel(Const("Назад")),
        state=TGSettingStates.MENU,
        getter=BlacklistThings.chats_getter,
    )
)

access_token_dialog = Dialog(
    Window(
        Const(
            "Скопируйте текущий токен или введите новый (можно получить с помощью https://vkhost.github.io/)"
        ),
        TextInput(
            "vk_apikey_input",
            type_factory=AccessTokenThings.str_access_token,
            # filter=F.text.regexp(AccessTokenThings.re_access_token),
            on_success=AccessTokenThings.correct_access_token,
            on_error=AccessTokenThings.wrong_access_token,
        ),
        Cancel(Const("Отмена")),
        getter=AccessTokenThings.on_write_token,
        state=TGSettingStates.ApiKey.SELECT,
        markup_factory=AccessTokenThings,
    ),
    Window(
        Format("Хотите сохранить токен?"),
        Cancel(Const("Да"), on_click=AccessTokenThings.save_access_token),
        Back(Const("Нет"), on_click=AccessTokenThings.remove_access_token),
        state=TGSettingStates.ApiKey.CONFIRM,
        markup_factory=AccessTokenThings,
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
                on_click=BlacklistThings.on_check_blacklist_click,
                # on_click=check_blacklist
            ),
            id="vk_blacklist_chats",
            width=1,
            height=CHATS_PAGE_LEN,
            on_page_changed=on_page_changed,
        ),
        Next(Const("Сохранить")),
        Cancel(Const("Отмена")),
        getter=chats_getter,
        state=TGSettingStates.Blacklist.SELECT,
    ),
    Window(
        Format(
            "Ваш выбор чатов: {chats_blacklist}. Хотите сохранить чёрный список?"
        ),
        Cancel(Const("Да"), on_click=BlacklistThings.save_blacklist),
        Back(Const("Нет")),
        state=TGSettingStates.Blacklist.CONFIRM,
        getter=BlacklistThings.on_selected_blacklist,
    ),
)


rt.include_routers(common_dialog, blacklist_dialog, access_token_dialog)
