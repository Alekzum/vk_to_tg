from . import config
from . import my_aiosqlitestore
from . import my_middlewares
from . import my_routers
from . import fsm_states
from . import my_vk


from bots.telegram_bot.utils.my_middlewares import CooldownMiddleware
from bots.telegram_bot.utils.my_aiosqlitestore import AioSQLStorage
from aiogram.client.default import DefaultBotProperties
from aiogram_dialog import setup_dialogs
from aiogram import Bot, Dispatcher
from utils.config import Config, OWNER_ID
from ..handlers import get_rt
import pathlib


async def get_bot() -> tuple[Bot, Dispatcher]:
    return await make_bot(), make_dispatcher()


async def make_bot():
    # bot_ = getattr(make_bot, "result", None)
    # if bot_ is not None:
    #     return bot_

    bot = Bot(
        token=(await Config(OWNER_ID).load_values())._BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="html"),
    )
    # setattr(make_bot, "result", bot)
    return bot


def make_dispatcher():
    # dp_ = getattr(make_dispatcher, "result", None)
    # if dp_ is not None:
    #     return dp_

    dp = Dispatcher(
        storage=AioSQLStorage(str(pathlib.Path("data", "fsm_storage.db"))),
        name="VkBottle",
    )

    dp.message.middleware(CooldownMiddleware(1))
    dp.callback_query.middleware(CooldownMiddleware(1))
    dp.include_router(get_rt())
    # include_routers(dp)
    dialog_bg_factory = setup_dialogs(dp)
    dp["dialog_bg_factory"] = dialog_bg_factory

    # setattr(make_dispatcher, "result", dp)
    return dp


__all__ = [
    "config",
    "my_aiosqlitestore",
    "my_middlewares",
    "my_routers",
    "fsm_states",
    "my_vk",
    "get_bot",
    "make_bot",
    "make_dispatcher",
]
