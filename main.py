from utils import runtime_platform, github
from utils.config import MyConfig
github.check_local_dir()

if runtime_platform.in_venv() or not github.restarted():
    exit(0)

from requests.exceptions import ReadTimeout, ConnectionError  # type: ignore[import-untyped]
import vk_api.longpoll   # type: ignore[import-untyped]

from handler.telegram import MyTelegram
import handler.vk as vk

import traceback
import logging
import vk_api


config = MyConfig()
logger = logging.getLogger(__name__)


def main():
    tgClient = MyTelegram()
    vkClient = vk_api.VkApi(token=config.access_token)
    
    vkApi = vkClient.get_api()

    vkLongpool = vk_api.longpoll.VkLongPoll(vkClient, wait=5)

    tgClient.send_text("Бот запущен!")
    logger.info("Бот запущен!")
    
    while True:
        try:
            listen(vkLongpool, vkApi, tgClient)

        except KeyboardInterrupt:
            tgClient.stop()
            logger.info("Бот остановлен.")
            raise
            break


def listen(vkLongpool: vk_api.longpoll.VkLongPoll, vkApi: vk_api.VkApi, tgClient: MyTelegram):
    try:
        for event in vkLongpool.listen():
            vk.handle(event, vkApi, tgClient)

    except (ReadTimeout, ConnectionError):
        pass

    except KeyboardInterrupt:
        raise
    
    except Exception as ex:
        ex_str = traceback.format_exc()[-4000:]
        error_str = "Ошибка!\n" + ex_str
        tgClient.send_text(error_str)
        logger.error(error_str)
        
    return
    

if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        main()
    except KeyboardInterrupt:
        print("Остановка бота...")
            
    # exit(0)