from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Next, Back, Row, Cancel
from aiogram_dialog.widgets.input import MessageInput

from aiogram_dialog.api.exceptions import NoContextError
from bots.telegram_bot.utils.fsm_states import BotStates, EchoStates
import logging


logger = logging.getLogger(__name__)
rt = Router()


async def echo_action(msg: Message, _, dialog_manager: DialogManager):
    dialog_manager.show_mode = ShowMode.EDIT
    await msg.copy_to(msg.chat.id)


common_dialog = Dialog(
    Window(
        Const("Just type something to me and I send same message"),
        Row(
            Cancel(Const("No")),
            Next(Const("ok")),
        ),
        state=EchoStates.MENU,
    ),
    Window(
        Const("Now write. I will wait..."),
        Back(Const("I changed my mind")),
        state=EchoStates.ECHO,
    ),
)


# @rt.message(StateFilter(None), Command("echo"))
# async def cmd_start(_: Message, dialog_manager: DialogManager):
#     try:
#         dialog_manager.current_context()
#     except NoContextError:
#         await dialog_manager.start(
#             BotStates.MENU,
#             mode=StartMode.,
#             show_mode=ShowMode.AUTO,
#         )


# @rt.message(~StateFilter(None), Command("cancel"))
# async def cancel_state(msg: Message, dialog_manager: DialogManager):
#     await dialog_manager.reset_stack()


rt.include_router(common_dialog)
