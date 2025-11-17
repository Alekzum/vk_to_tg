from bots.vk_bot.main import main as vk_bot_main
from bots.telegram_bot.main import main as tg_bot_main
from utils.config import OWNER_ID
from utils.my_exceptions import handle_exception
from utils.my_logging import IS_LOUD, getLogger
from utils.my_wraps import wrap_loggers
import asyncio
import sys


logger = getLogger(__name__)


async def checker(*tasks: asyncio.Task):
    while True:
        for task in tasks:
            if not task.done():
                continue
            exception = task.exception()
            if not exception or isinstance(exception, KeyboardInterrupt):
                continue
            raise exception
        await asyncio.sleep(1)


async def main():
    wrap_loggers()
    # test()
    if ("--telegram" not in sys.argv[1:]) and (
        "--test" in sys.argv[1:] or "--vk" in sys.argv[1:]
    ):
        logger.info("Стартует только ВК бот")
        task = asyncio.create_task(vk_bot_main(OWNER_ID))
    else:
        logger.info("Стартует ТГ бот")
        task = asyncio.create_task(tg_bot_main())

    try:
        await checker(task)
    except asyncio.CancelledError:
        logger.info("task1 is cancelled")
    except KeyboardInterrupt:
        logger.info("task1 is quitted")
    except Exception as ex:
        handle_exception(ex)
        raise ex


if __name__ == "__main__":
    logger.info("Запуск бота...")
    asyncio.run(main(), debug=IS_LOUD)
