from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.utils import formatting
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Next, Back, Row, Start, Cancel
from aiogram_dialog.widgets.input import MessageInput

from aiogram_dialog.api.exceptions import NoContextError
from bots.telegram_bot.utils.fsm_states import (
    CommonStates,
    EchoStates,
    BotStates,
    SettingStates,
)
import logging


logger = logging.getLogger(__name__)
rt = Router()


HELP_MENU = formatting.as_marked_section(
    "That you can do:",
    "Make act me like echo-bot (repeat messages)",
    "Start getting messages from VK via me",
    "Tune my settings (VK's token for example)",
).as_html()


async def echo_action(msg: Message, _, dialog_manager: DialogManager):
    dialog_manager.show_mode = ShowMode.EDIT
    await msg.copy_to(msg.chat.id)


common_dialog = Dialog(
    Window(
        Const("Hello! I an multifunctional bot (for now, later just VK-bot)."),
        Next(Const("Ok and?")),
        state=CommonStates.START,
    ),
    Window(
        Const(HELP_MENU),
        Start(text=Const("Repeat messages"), id="echo_menu", state=EchoStates.MENU),
        Start(text=Const("Start getting messages"), id="bot_menu", state=BotStates.MENU),
        Start(text=Const("Settings"), id="settings_menu", state=SettingStates.MENU),
        state=CommonStates.MENU,
    ),
)

repeat_dialog = Dialog(
    Window(
        Const("Just type something to me and I send same message"),
        Row(
            Cancel(Const("Cancel")),
            Next(Const("Ok")),
        ),
        state=EchoStates.MENU,
    ),
    Window(
        Const("Now write. I will wait..."),
        Back(Const("I changed my mind")),
        MessageInput(echo_action),
        state=EchoStates.ECHO,
    ),
)


@rt.message(StateFilter(None), Command("start"))
async def cmd_start(_: Message, dialog_manager: DialogManager):
    try:
        dialog_manager.current_context()
    except NoContextError:
        await dialog_manager.start(
            CommonStates.START,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.AUTO,
        )


@rt.message(~StateFilter(None), Command("cancel"))
async def cancel_state(msg: Message, dialog_manager: DialogManager):
    await dialog_manager.reset_stack()


rt.include_router(common_dialog)
