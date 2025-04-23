from .utils import get_bot
import pathlib
import asyncio


handlers_directory = pathlib.Path("bots/telegram_bot/handlers")
# current_file = pathlib.Path(__file__)
# handlers_directory = current_file.absolute().parent.joinpath("handlers")


# async def get_bot() -> tuple[Bot, Dispatcher]:
#     bot = Bot(
#         token=(await Config(OWNER_ID).load_values())._BOT_TOKEN,
#         default=DefaultBotProperties(parse_mode="html"),
#     )
#     dp = Dispatcher(storage=SQLStorage())
#     dp.include_router(rt)
#     # include_routers(dp, str(handlers_directory))

#     dp.message.middleware(CooldownMiddleware(1))
#     dp.callback_query.middleware(CooldownMiddleware(10))

#     return bot, dp


async def main():
    bot, dp = await get_bot()
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
