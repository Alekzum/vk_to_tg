from aiogram import Router, Bot, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ReplyParameters, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.text import Const, Multi, Format
from aiogram_dialog.widgets.kbd import Next, Back, Row, Cancel, Button
from aiogram_dialog.widgets.input import MessageInput

from aiogram_dialog.api.exceptions import NoContextError
from ..utils.fsm_states import BotStates, EchoStates, SettingStates
from utils.interface import get_users
from utils.interface.vk_messages import get_vk_id
from utils.interface.user_settings import set_longpoll_state, get_longpoll_state
from utils.config import Config
# from ...vk_bot.main import get_client_and_longpoll
# from ...vk_bot.handlers import get_caches
from vk_api import vk_api
from ...vk_bot.classes import Message as VkMessage

# from bots import vk_bot
from contextlib import suppress
import logging
import asyncio


logger = logging.getLogger(__name__)
rt = Router()

tasks: dict[int, asyncio.Task] = dict()


@rt.startup()
async def start_polls(bot: Bot):
    from bots.vk_bot.main import main

    users = await get_users()
    for user in users:
        if user.pooling_state:
            await bot.send_message(user.tg_id, "начато получение сообщений...")
            task = asyncio.create_task(main(user.tg_id))
            tasks[user.tg_id] = task


@rt.shutdown()
async def stop_polls(bot: Bot):
    if not tasks:
        return
    
    plain_tasks = list(tasks.values())

    done, pending = await asyncio.wait(plain_tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        # (mostly) Graceful shutdown unfinished tasks
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    # Wait finished tasks to propagate unhandled exceptions
    await asyncio.gather(*done)


async def turn_off_polling(dialog_manager: DialogManager, bot: Bot, *args, **kwargs):
    user = dialog_manager.event.from_user
    assert user
    result = await get_longpoll_state(user.id)
    if not result:
        return dict(message="Не нашли необходимые данные :(")

    polling_state, ts, pts = result
    if polling_state and tasks.get(user.id):
        task = tasks[user.id]

        msg = await bot.send_message(user.id, "Останавливаем получение сообщений...")
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await set_longpoll_state(user.id, False, ts, pts)
        await msg.delete()

        return dict(message="Получение сообщений остановлено")
    return dict(message="Получение сообщений уже остановлено")


async def turn_on_polling(dialog_manager: DialogManager, *args, **kwargs):
    user = dialog_manager.event.from_user
    assert user
    result = await get_longpoll_state(user.id)
    if not result:
        return dict(message="Не нашли необходимые данные :(")
    polling_state, ts, pts = result

    if not polling_state and not tasks.get(user.id):
        from bots.vk_bot.main import main
        task = asyncio.create_task(main(user.id))
        tasks[user.id] = task
        result = await set_longpoll_state(user.id, True, ts, pts)
        assert result

        return dict(message="Получение сообщений начато")
    return dict(message="Получение сообщений уже идёт")


async def wrong_answer(msg: Message, message_input: MessageInput, dialog_manager: DialogManager):
    await msg.answer("Надо отправить с ответом на сообщение.")


async def maybe_answer(msg: Message, message_input: MessageInput, dialog_manager: DialogManager):
    assert msg.reply_to_message
    dialog_manager.dialog_data["reply_text"] = msg.md_text
    dialog_manager.dialog_data["reply_id"] = msg.reply_to_message.message_id
    # dialog_manager.dialog_data["reply_in"] = msg.reply_to_message.message_id
    await dialog_manager.next()


async def send_ask(**kwargs):
    return dict()


# CallbackQuery, "Button", DialogManager
async def send_confirm(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    user_id = callback.from_user.id

    msg_text = dialog_manager.dialog_data["reply_text"]
    msg_tg_id = dialog_manager.dialog_data["reply_to"]
    msg_vk_id = await get_vk_id(tg_msg_id=msg_tg_id, tg_chat_id=user_id)
    
    config = Config(user_id)
    await config.load_values()
    token = config._ACCESS_TOKEN
    vk_client = vk_api.VkApi(token=token)
    api = vk_client.get_api()


    raw_msg = api.messages.getById(message_ids=msg_vk_id)
    vk_msg = VkMessage(**raw_msg)
    out_msg = api.messages.send(peer_id=vk_msg.peer_id, random_id=vk_msg.random_id, message=msg_text)
    return dict(message=f"отправленнео сообщение: {out_msg}")


async def send_cancel(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    return dict(message=f"ладно")
    # pass


common_dialog = Dialog(
    Window(
        Multi(
            Const("Что бы начать получение сообщений, нажмите \"далее\""),
            Format("{message}", when="message"),
        ),
        Row(
            Cancel(Const("Назад")),
            Next(Const("Далее")),
        ),
        state=BotStates.MENU,
        getter=turn_off_polling,
    ),
    Window(
        Multi(
            Const("Получаем сообщения..."),
            Format("{message}", when="message"),
        ),
        Back(Const("Отмена")),
        MessageInput(wrong_answer, filter=~F.reply_to_message),
        MessageInput(maybe_answer, filter=F.reply_to_message.from_user.is_bot),
        state=BotStates.START_POLLING,
        getter=turn_on_polling,
        preview_add_transitions=[Next()],
    ),
    Window(
        # Multi(
        Format("Отправить сообщение с текстом {text}?"),
        Back(Const("Нет"), on_click=send_cancel),
        Back(Const("Да"), on_click=send_confirm),
        state=BotStates.ANSWER,
        getter=send_ask,
    ),
)

settings_dialog = Dialog(Window(state=SettingStates.MENU))


rt.include_router(common_dialog)
