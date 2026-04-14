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
    return Bot(
        token=(await Config(OWNER_ID).load_values())._BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="html"),
    )


def make_dispatcher():
    dp = Dispatcher(
        storage=AioSQLStorage(str(pathlib.Path("data", "fsm_storage.db"))),
        name="VkBottle",
    )

    dp.message.middleware(CooldownMiddleware(1))
    dp.callback_query.middleware(CooldownMiddleware(1))
    dp.include_router(get_rt())
    # include_routers(dp)
    setup_dialogs(dp)

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
