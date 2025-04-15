from bots.vk_bot.main import main as vk_bot_main
from bots.telegram_bot.main import main as tg_bot_main
from utils.config import OWNER_ID
from utils.my_exceptions import handle_exception
import threading
import logging


logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        vk_bot_main(OWNER_ID)
        # thread1 = threading.Thread(target=vk_bot_main, name=f"retranslator for id {OWNER_ID}", args=(OWNER_ID,))
        # thread2 = threading.Thread(target=tg_bot_main, name=f"telegram bot", args=())
        # main(OWNER_ID)
        # thread1.start()
        # thread2.start()

        # thread1.join()
        # thread2.join()
    except KeyboardInterrupt:
        logger.info("Бот остановлен.")
    except Exception as ex:
        handle_exception(ex)
        raise
