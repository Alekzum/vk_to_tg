from bots.vk_bot.main import main as vk_bot_main
from bots.vk_bottle.main import main as vk_bottle_main
from bots.telegram_bot.main import main as tg_bot_main
from utils.config import OWNER_ID
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
            if not exception:
                continue
            raise exception
        await asyncio.sleep(1)


async def main():
    wrap_loggers()
    # test()
    sys_args = sys.argv[1:]
    # task: asyncio.Task

    only_telegram = "--telegram" in sys_args
    is_test = "--test" in sys_args
    is_vk = "--vk" in sys_args

    via_vkbottle = "--vkbottle" in sys_args
    run_only_vk = (not only_telegram) and (is_test or is_vk)

    async def run():
        if run_only_vk and via_vkbottle:
            logger.info("Стартует только ВК бот (через vkbottle)")
            await vk_bottle_main(OWNER_ID)
        elif run_only_vk:
            logger.info("Стартует только ВК бот")
            await vk_bot_main(OWNER_ID)
        # elif via_vkbottle:
        #     logger.info("Стартует ТГ бот (+vkbottle)")
        #     task = asyncio.create_task(tg_bot_main())
        else:
            logger.info("Стартует ТГ бот")
            await tg_bot_main()

    try:
        await run()
        # task = asyncio.create_task(run())
        # await task
    except asyncio.CancelledError:
        logger.info("task1 is cancelled")
    except KeyboardInterrupt:
        logger.info("task1 is quitted")
    # try:
    #     await checker(task)
    # except asyncio.CancelledError:
    #     logger.info("task1 is cancelled")
    # except KeyboardInterrupt:
    #     logger.info("task1 is quitted")
    # except Exception as ex:
    #     handle_exception(ex)
    #     raise ex


if __name__ == "__main__":
    logger.info("Запуск бота...")
    asyncio.run(main(), debug=bool(IS_LOUD))
