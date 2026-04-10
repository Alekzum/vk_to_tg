from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, ReplyParameters
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Const, Multi, Format
from aiogram_dialog.widgets.kbd import (
    Next,
    Back,
    Row,
    Cancel,
)
from aiogram_dialog.widgets.input import MessageInput

# from ..utils.my_vk import get_vk_api
from ..utils.my_typings import get_vk_api, get_dialog_name
from ..utils.fsm_states import BotStates

# from ...vk_bot.my_async_functions import get_dialog_name
from utils.interface import get_users
from utils.interface import vk_interface
from utils.interface.user_settings import (
    set_polling_state,
    get_polling_state,
)
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
# Polling
@rt.startup()
async def start_polls(bot: Bot):
    from bots.vk_bot.main import main

    users = await get_users()
    for user in users:
        logger.debug(
            "polling_state",
            user_polling_state=user.polling_state,
            user_id=user.tg_id,
        )
        if user.polling_state:
            logger.info("starting polling...", user_id=user.tg_id)
            msg = await bot.send_message(
                user.tg_id, "Начато получение сообщений..."
            )
            task = create_task_helper(
                main(user.tg_id), name=f"polling_{user.tg_id}"
            )
            tasks[user.tg_id] = task
            await msg.delete()


# region stop_polls
@rt.shutdown()
async def stop_polls(bot: Bot):
    if not tasks:
        return

    for task in tasks.values():
        task.cancel("stopping bot...")

    await asyncio.gather(*tasks.values(), return_exceptions=False)


ecranize_regex = re.compile(r"\\([\`\*\_\{\}\[\]\\(\)\#\+\-\.\!])")


# region get_tg_msg_text
def get_tg_msg_text(message: Message) -> str:
    return ecranize_regex.sub("\\1", message.md_text)


# region on_menu
async def on_menu(dialog_manager: DialogManager, bot: Bot, *args, **kwargs):
    user = dialog_manager.event.from_user
    assert user
    polling_state = await get_polling_state(user.id)
    if polling_state is None:
        return dict(message="Не нашли необходимые данные :(")

    # if polling_state and tasks.get(user.id):
    if polling_state:
        task = tasks[user.id]

        msg = await bot.send_message(
            user.id, "Останавливаем получение сообщений..."
        )
        task.cancel("Stopping bot...")
        await set_polling_state(user.id, False)
        with suppress(asyncio.CancelledError):
            await task
        await msg.delete()

        return dict(message="Получение сообщений остановлено")
    return dict(message="Получение сообщений уже остановлено")


# region on_start_polling
async def on_start_polling(dialog_manager: DialogManager, *args, **kwargs):
    user = dialog_manager.event.from_user
    assert user
    result = await get_polling_state(user.id)
    if result is None:
        return dict(message="Не нашли необходимые данные :(")
    polling_state = result

    # if not polling_state and not tasks.get(user.id):
    if not polling_state:
        from bots.vk_bot.main import main

        task = create_task_helper(main(user.id))
        tasks[user.id] = task
        await set_polling_state(user.id, True)

        return dict(message="Получение сообщений начато")
    return dict(message="Получение сообщений уже идёт")


# region maybe_reply_photo
# TODO: combine reply and send segments
# it's near to impossible - i'll need to use a lot of "if" statements
## Reply section
async def maybe_reply_photo(  # IDK ABOUT THIS.
    msg: Message, message_input: MessageInput, dialog_manager: DialogManager
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
        mgs_caption=get_tg_msg_text(msg),
        mgs_to=vk_id,
        msg_in=vk_message.peer_id,
        mgs_name=await get_dialog_name(api, vk_message.peer_id),
    )
    dialog_manager.dialog_data.update(msg_data)
    await dialog_manager.start(BotStates.Answer.SEND_MESSAGE, data=msg_data)


# region maybe_reply_text
async def maybe_reply_text(
    msg: Message, message_input: MessageInput, dialog_manager: DialogManager
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
        msg_text=get_tg_msg_text(msg),
        msg_to=vk_id,
        msg_in=vk_message.peer_id,
        msg_name=await get_dialog_name(api, vk_message.peer_id),
    )
    dialog_manager.dialog_data.update(msg_data)
    await dialog_manager.start(BotStates.Answer.SEND_MESSAGE, data=msg_data)


# region maybe_send_photo
## Send section
async def maybe_send_photo(  # IDK ABOUT THIS.
    msg: Message, message_input: MessageInput, dialog_manager: DialogManager
):
    if not (photos := msg.photo):
        return

    msg_data = dict(
        msg_act="send",
        msg_type="photo",
        msg_photo=max(photos, key=lambda x: x.height).file_id,
        msg_text=get_tg_msg_text(msg),
        msg_to=None,
        msg_in=None,
        msg_name=None,
    )
    dialog_manager.dialog_data.update(msg_data)
    if dialog_manager.dialog_data["msg_act"] != "send":
        raise RuntimeError

    await dialog_manager.start(
        BotStates.Answer.MAYBE_CHOOSE_CHAT, data=msg_data
    )


# region maybe_send_text
async def maybe_send_text(
    msg: Message, message_input: MessageInput, dialog_manager: DialogManager
):
    msg_data = dict(
        msg_act="send",
        msg_type="text",
        msg_text=get_tg_msg_text(msg),
        msg_to=None,
        msg_in=None,
        msg_name=None,
    )
    dialog_manager.dialog_data.update(msg_data)

    await dialog_manager.start(
        BotStates.Answer.MAYBE_CHOOSE_CHAT, data=msg_data
    )


maybe_inputs = (
    MessageInput(
        maybe_reply_photo, filter=F.reply_to_message.from_user.is_bot & F.photo
    ),
    MessageInput(
        maybe_reply_text, filter=F.reply_to_message.from_user.is_bot & F.text
    ),
    MessageInput(maybe_send_photo, filter=~F.reply_to_message & F.photo),
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
        state=BotStates.MENU,
        getter=on_menu,
    ),
    Window(
        Multi(
            Const("Получаем сообщения..."),
            Format("{message}", when="message"),
        ),
        Back(Const("Отмена")),
        *maybe_inputs,
        state=BotStates.START_POLLING,
        getter=on_start_polling,
        preview_add_transitions=[Next()],
    ),
)


rt.include_router(common_dialog)
