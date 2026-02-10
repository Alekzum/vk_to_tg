from aiogram import Router, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, ErrorEvent
from aiogram.utils import formatting
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Next, Start
from utils.config import OWNER_ID

from aiogram_dialog.api.exceptions import NoContextError
from ..utils.fsm_states import (
    CommonStates,
    EchoStates,
    BotStates,
    SettingStates,
)
import structlog
from utils.my_logging import getLogger
import logging
import traceback
from html import escape


logger = getLogger(__name__)
rt = Router(name=__name__)


HELP_MENU = formatting.as_marked_section(
    "That you can do:",
    "Use as echo-bot (repeat messages)",
    "Start getting messages from VK",
    "Tune settings (VK's token for example)",
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
        Start(text=Const("Start getting messages"), id="bot_menu", state=BotStates.MENU),
        Start(text=Const("Settings"), id="settings_menu", state=SettingStates.MENU),
        Start(text=Const("Repeat messages"), id="echo_menu", state=EchoStates.MENU),
        state=CommonStates.MENU,
    ),
)

# repeat_dialog = Dialog(
#     Window(
#         Const("Just type something to me and I send same message"),
#         Row(
#             Cancel(Const("Cancel")),
#             Next(Const("Ok")),
#         ),
#         state=EchoStates.MENU,
#     ),
#     Window(
#         Const("Now write. I will wait..."),
#         Back(Const("I changed my mind")),
#         MessageInput(echo_action),
#         state=EchoStates.ECHO,
#     ),
# )


@rt.error()
async def error_handler(error: ErrorEvent, bot: Bot):
    logger.critical(f"Critical error caused by %s", error.exception, exc_info=True)
    # error_message = f"Critical error caused by %s" % error.exception
    # await bot.send_message(OWNER_ID, )

    error_str = "".join(traceback.format_exception(error.exception, limit=3))
    for chunk in [error_str[i*4096:(i+1)*4096] for i in range(len(error_str)//4096)]:
        await bot.send_message(OWNER_ID, escape(chunk))
    # logger.error("exception", error_exception=error.exception)


# @rt.error
# async def exception_handler(bot: Bot, *args, **kwargs):
#     msg=f"{args=}, {kwargs=}"
#     logger.warning(msg)
#     await bot.send_message(OWNER_ID, msg)
#     # pass


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
