from utils.config import Config, OWNER_ID
from bots.telegram_bot.utils.my_routers import include_routers
from bots.telegram_bot.utils.my_middlewares import CooldownMiddleware
from aiogram_sqlite_storage.sqlitestore import SQLStorage  # type: ignore
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher
import pathlib
import asyncio


handlers_directory = pathlib.Path("bots/telegram_bot/handlers")
# current_file = pathlib.Path(__file__)
# handlers_directory = current_file.absolute().parent.joinpath("handlers")


def get_bot() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=Config(OWNER_ID)._BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="html"),
    )
    dp = Dispatcher(storage=SQLStorage())
    include_routers(dp, str(handlers_directory))

    dp.message.middleware(CooldownMiddleware(1))
    dp.callback_query.middleware(CooldownMiddleware(10))

    return bot, dp


async def main_():
    bot, dp = get_bot()
    await dp.start_polling(bot)


def main():
    try:
        asyncio.run(main_())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
