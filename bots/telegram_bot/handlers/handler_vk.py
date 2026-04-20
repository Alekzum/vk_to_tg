import html
from typing import Any, Callable, TypeIs

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, ReplyParameters
from aiogram_dialog import (
    BaseDialogManager,
    Dialog,
    Window,
    DialogManager,
    BgManagerFactory,
)
from aiogram_dialog.widgets.text import Const, Multi, Format
from aiogram_dialog.widgets.kbd import (
    Next,
    Back,
    Row,
    Cancel,
)
from aiogram_dialog.widgets.input import MessageInput
from pyrogram import types

from bots.telegram_bot.classes import MyTelegram
from utils.config import Config

# from ..utils.my_vk import get_vk_api
from ..utils.my_vk_classes import get_vk_api, get_dialog_name
from ..utils.fsm_states import VKBotStates

# from ...vk_bot.my_async_functions import get_dialog_name
from utils.interface import get_users
from utils.interface import vk_interface
from utils.interface.user_settings import UserSettingsManager
from utils.my_exceptions import create_task_helper
from contextlib import suppress
import asyncio
from utils.my_logging import getLogger
import re


logger = getLogger(__name__)
rt = Router(name=__name__)

tasks: dict[int, asyncio.Task] = dict()
CHATS_PAGE_LEN = 6


# region edit_message
# read button
@rt.edited_message()
async def edit_message():
    pass


# region read_message
@rt.callback_query(
    F.data.startswith("read") & F.data.split(":")[1:].as_("data")
)
async def read_message(
    callback_query: CallbackQuery, bot: Bot, data: list[str]
):
    async def answer(text):
        await callback_query.answer(text)
        if callback_query.message:
            return await callback_query.message.answer(
                text,
                reply_parameters=ReplyParameters(
                    message_id=callback_query.message.message_id
                ),
            )
        return None

    usr = callback_query.from_user
    # usr = msg.from_user.id
    logger.debug("read_message", user_id={usr.id})
    vk_peer_id, vk_msg_id = int(data[0]), int(data[1])

    api = await get_vk_api(user_id=usr.id)

    if vk_peer_id is None:
        return await answer("Not found conversation")
    conversation = await api.get_conversation(peer_id=vk_peer_id)
    if not conversation:
        return await answer("Not found conversation")
    elif conversation["in_read"] >= vk_msg_id:
        if isinstance(callback_query.message, Message):
            await callback_query.message.edit_reply_markup()
        return await answer("Message already read")

    vk_message = await api.get_message(message_ids=[vk_msg_id])
    if not vk_message:
        return await answer("Not found message")
    elif vk_message[0].peer_id != vk_peer_id:
        return await answer("Invalid message's peer_id (somehow)")

    msg = await answer("Reading message...")
    await api.read_message(peer_id=vk_peer_id, message_id=vk_msg_id)
    if isinstance(callback_query.message, Message):
        await callback_query.message.edit_reply_markup()

    await vk_interface.mark_vk_msg_as_read(
        tg_chat_id=usr.id, vk_msg_id=vk_msg_id
    )
    if isinstance(callback_query.message, Message):
        await callback_query.message.edit_reply_markup()
    if msg:
        await msg.delete()


# region start_polls
async def prepare_done_callback(user_id: int, bg_manager: BaseDialogManager):
    """Maker for function to `task.add_done_callback()`.
    It'll check - VK fetcher finished with exception or not.

    If it with exception then Background Dialog Manager will
    set user's state/window into "before polling" and send
    notification about exception

    Else just send notification about success finish

    Args:
        user_id (int): User's ID
        bg_manager (BaseDialogManager): Background manager

    Returns:
        Callable: Function to provide into `task.add_done_callback()`
    """
    tg = MyTelegram(chat_id=user_id)
    await tg.init()

    def is_exception(obj: Any) -> TypeIs[BaseException]:
        return isinstance(obj, BaseException)

    def task_post_run(future: asyncio.Task[Any]):
        if future.cancelled():
            ex = None
        else:
            ex = future.exception()

        async def inner(ex: BaseException | None = None):
            if not is_exception(ex):
                return await tg.send_text(
                    "Получение сообщений благополучно завершено"
                )
            await tg.send_text(
                f"Получение сообщений досрочно завершено из-за ошибки {html.escape(str(ex))}"
            )
            await UserSettingsManager(user_id).state.set(False)
            await bg_manager.switch_to(VKBotStates.BEFORE_POLLING)

        return future.get_loop().create_task(inner(ex=ex))

    return task_post_run


# Polling
@rt.startup()
async def start_polls(bot: Bot, dialog_bg_factory: BgManagerFactory):

    users = await get_users()
    for user in users:
        bg_manager = dialog_bg_factory.bg(
            bot, user_id=user.tg_id, chat_id=user.tg_id
        )
        polling_state_manager = UserSettingsManager(user.tg_id).polling_state
        if await polling_state_manager.get():
            await polling_state_manager.set(False)
            await run_task(bot=bot, user_id=user.tg_id, bg_manager=bg_manager)


async def run_task(bot: Bot, user_id: int, bg_manager: BaseDialogManager):
    """Run user's VK fetcher. User's polling state should be False to run

    Args:
        bot (Bot): Telegram bot
        user_id (int): User's ID
        bg_manager (BaseDialogManager): To provide into function `prepare_done_callback`\
        for sending user into previous state in case of exception at running\
        VK fetcher
    """
    from bots.vk_bot.main import main

    config = await Config.load_user_values(user_id)
    logger.debug(
        "polling_state",
        user_polling_state=config.polling_state,
        user_id=user_id,
    )
    polling_state_manager = UserSettingsManager(user_id).polling_state
    # breakpoint()
    task_done_callback: Callable[
        ..., asyncio.Task[types.Message | None]
    ] = await prepare_done_callback(
        user_id=config.chat_id, bg_manager=bg_manager
    )
    if not config.polling_state:
        await polling_state_manager.set(True)
        logger.info("starting polling...", user_id=config.chat_id)
        # msg = \
        await bot.send_message(config.chat_id, "Начато получение сообщений...")
        task = create_task_helper(
            main(config.chat_id), name=f"polling_{config.chat_id}"
        )
        tasks[config.chat_id] = task
        # await task
        task.add_done_callback(lambda _: tasks.pop(config.chat_id, None))
        task.add_done_callback(task_done_callback)


# region stop_polls
@rt.shutdown()
async def stop_polls(bot: Bot, **kwargs):
    logger.debug("checking on shutdown", kwargs=kwargs)
    if not tasks:
        return

    for task in tasks.values():
        task.cancel("stopping bot...")

    await asyncio.gather(*tasks.values(), return_exceptions=False)


class HandlerVKThings:
    escape_regex = re.compile(r"\\([\`\*\_\{\}\[\]\\(\)\#\+\-\.\!])")

    # region get_tg_msg_text
    @staticmethod
    def get_tg_msg_text(message: Message) -> str:
        return HandlerVKThings.escape_regex.sub("\\1", message.md_text)

    # region maybe_reply_photo
    # TODO: combine reply and send segments
    # it's near to impossible - i'll need to use a lot of "if" statements
    # # Reply section
    @staticmethod
    async def maybe_reply_photo(  # IDK ABOUT THIS.
        msg: Message, message_input: MessageInput, manager: DialogManager
    ):
        if not (usr := msg.from_user):
            return
        if not (photos := msg.photo):
            return
        if not (rtm := msg.reply_to_message):
            return

        # usr = msg.from_user.id
        logger.debug("maybe_answer", user_id={usr.id})

        vk_id = await vk_interface.get_vk_id(
            tg_chat_id=msg.chat.id, tg_msg_id=rtm.message_id
        )
        if vk_id is None:
            return await msg.answer("Я не знаю такое сообщение :(")

        api = await get_vk_api(user_id=usr.id)

        vk_message = await api.get_message(message_ids=vk_id)

        msg_data = dict(
            mgs_act="reply",
            mgs_type="photo",
            mgs_photos=max(photos, key=lambda x: x.height).file_id,
            mgs_caption=HandlerVKThings.get_tg_msg_text(msg),
            mgs_to=vk_id,
            msg_in=vk_message.peer_id,
            mgs_name=await get_dialog_name(api, vk_message.peer_id),
        )
        manager.dialog_data.update(msg_data)
        await manager.start(VKBotStates.Answer.SEND_MESSAGE, data=msg_data)

    # region maybe_reply_text
    @staticmethod
    async def maybe_reply_text(
        msg: Message, message_input: MessageInput, manager: DialogManager
    ):
        assert (rtm := msg.reply_to_message)
        if not (usr := msg.from_user):
            return

        # usr = msg.from_user.id
        logger.debug("maybe_answer", user_id={usr.id})

        vk_id = await vk_interface.get_vk_id(
            tg_chat_id=msg.chat.id, tg_msg_id=rtm.message_id
        )
        if vk_id is None:
            return await msg.answer("Я не знаю такое сообщение :(")

        api = await get_vk_api(user_id=usr.id)
        vk_message = await api.get_message(message_ids=vk_id)
        msg_data = dict(
            msg_act="reply",
            msg_type="text",
            msg_text=HandlerVKThings.get_tg_msg_text(msg),
            msg_to=vk_id,
            msg_in=vk_message.peer_id,
            msg_name=await get_dialog_name(api, vk_message.peer_id),
        )
        manager.dialog_data.update(msg_data)
        await manager.start(VKBotStates.Answer.SEND_MESSAGE, data=msg_data)

    # region maybe_send_photo
    # # Send section
    @staticmethod
    async def maybe_send_photo(  # IDK ABOUT THIS.
        msg: Message, message_input: MessageInput, manager: DialogManager
    ):
        if not (photos := msg.photo):
            return

        msg_data = dict(
            msg_act="send",
            msg_type="photo",
            msg_photo=max(photos, key=lambda x: x.height).file_id,
            msg_text=HandlerVKThings.get_tg_msg_text(msg),
            msg_to=None,
            msg_in=None,
            msg_name=None,
        )
        manager.dialog_data.update(msg_data)
        if manager.dialog_data["msg_act"] != "send":
            raise RuntimeError

        await manager.start(VKBotStates.Answer.MAYBE_CHOOSE_CHAT, data=msg_data)

    # region maybe_send_text
    @staticmethod
    async def maybe_send_text(
        msg: Message, message_input: MessageInput, manager: DialogManager
    ):
        msg_data = dict(
            msg_act="send",
            msg_type="text",
            msg_text=HandlerVKThings.get_tg_msg_text(msg),
            msg_to=None,
            msg_in=None,
            msg_name=None,
        )
        manager.dialog_data.update(msg_data)

        await manager.start(VKBotStates.Answer.MAYBE_CHOOSE_CHAT, data=msg_data)

    # region on_menu
    @staticmethod
    async def on_before_polling(
        manager: DialogManager, bot: Bot, *args, **kwargs
    ):
        user: types.User = manager.middleware_data["user"]
        assert user
        polling_state_manager = UserSettingsManager(user.id).polling_state
        polling_state = await polling_state_manager.get()
        if polling_state is None:
            return dict(message="Не нашли необходимые данные :(")

        ctx = manager.current_context()
        prev_state = ctx.state.group._get_all_states()[
            ctx.state.group._get_all_states().index(ctx.state) - 1
        ]
        if prev_state is VKBotStates.POLLING:
            prev_text = "Получение сообщений уже остановлено"
        else:
            prev_text = "Получение сообщений выключено"

        if not polling_state:
            return dict(message=prev_text)
        task = tasks[user.id]

        msg = await bot.send_message(
            user.id, "Останавливаем получение сообщений..."
        )
        task.cancel("Stopping bot...")
        await polling_state_manager.set(False)
        with suppress(asyncio.CancelledError):
            await task
        await msg.delete()

        return dict(message="Получение сообщений остановлено")

    # region on_start_polling
    @staticmethod
    async def on_polling(bot: Bot, manager: DialogManager, *args, **kwargs):
        user: types.User = manager.middleware_data["user"]
        assert user
        polling_state_manager = UserSettingsManager(user.id).polling_state
        result = await polling_state_manager.get()
        if result is None:
            return dict(message="Не нашли необходимые данные :(")

        ctx = manager.current_context()
        prev_state = ctx.state.group._get_all_states()[
            ctx.state.group._get_all_states().index(ctx.state) - 1
        ]
        if prev_state is VKBotStates.BEFORE_POLLING:
            new_text = "Получение сообщений запущено"
        else:
            new_text = "Получение сообщений уже идёт"

        polling_state = result

        # if not polling_state and not tasks.get(user.id):
        if not polling_state:
            await run_task(bot=bot, user_id=user.id, bg_manager=manager)
            return dict(message="Получение сообщений начато")
        return dict(message=new_text)

    maybe_inputs = (
        MessageInput(
            maybe_reply_photo,
            filter=F.reply_to_message.from_user.is_bot & F.photo,
        ),
        MessageInput(
            maybe_reply_text,
            filter=F.reply_to_message.from_user.is_bot & F.text,
        ),
        MessageInput(
            maybe_send_photo,
            filter=~F.reply_to_message & F.photo,
        ),
        MessageInput(maybe_send_text, filter=~F.reply_to_message & F.text),
    )

    common_dialog = Dialog(
        Window(
            Multi(
                Const('Что бы начать получение сообщений, нажмите "далее"'),
                Format("{message}", when="message"),
            ),
            *maybe_inputs,
            Row(
                Cancel(Const("Назад")),
                Next(Const("Далее")),
            ),
            state=VKBotStates.BEFORE_POLLING,
            getter=on_before_polling,
        ),
        Window(
            Multi(
                Const("Получаем сообщения..."),
                Format("{message}", when="message"),
            ),
            Back(Const("Отмена")),
            *maybe_inputs,
            state=VKBotStates.POLLING,
            getter=on_polling,
            preview_add_transitions=[Next()],
        ),
    )


rt.include_router(HandlerVKThings.common_dialog)
