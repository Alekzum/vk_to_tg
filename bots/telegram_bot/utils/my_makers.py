from bots.telegram_bot.utils.config import get_token
from bots.telegram_bot.utils.my_routers import include_routers
from bots.telegram_bot.utils.my_middlewares import CooldownMiddleware
from bots.telegram_bot.utils.my_aiosqlitestore import AioSQLStorage
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram_dialog import setup_dialogs
import pathlib


def make_bot():
    return Bot(token=get_token(), default=DefaultBotProperties(parse_mode="html"))


def make_dispatcher():
    dp = Dispatcher(storage=AioSQLStorage(str(pathlib.Path("data", "fsm_storage.db"))))

    dp.message.middleware(CooldownMiddleware(1))
    dp.callback_query.middleware(CooldownMiddleware(1))
    include_routers(dp)
    setup_dialogs(dp)

    return dp
