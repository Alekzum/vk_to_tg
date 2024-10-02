from utils import runtime_platform, github
from utils.config import MyConfig
github.check_local_dir()
runtime_platform.check_platform()

if not github.restarted() or not runtime_platform.in_venv():
    exit(1)

from requests.exceptions import ReadTimeout, ConnectionError  # type: ignore[import-untyped]
import vk_api.longpoll   # type: ignore[import-untyped]

from handler.telegram import MyTelegram
import handler.vk as vk

import traceback
import logging
import vk_api


config = MyConfig()
logger = logging.getLogger(__name__)
WAIT_TIME = 1


def log(text: str) -> None:
    import datetime
    print(f"{str(datetime.datetime.now())[:-3]} - main.py - {text}")


def main():
    tgClient = MyTelegram()
    try:
        _main(tgClient)

    except KeyboardInterrupt:
        tgClient.stop()
        logger.info("Бот остановлен.")
    
    except Exception as ex:
        ex_str = traceback.format_exc()
        error_str = "\n".join([f"Ошибка! {ex_str}"])
        tgClient.send_text(error_str[-4090:])
        logger.error(error_str)
    


def _main(tgClient: MyTelegram):
    vkClient = vk_api.VkApi(token=config.access_token)
    
    vkApi = vkClient.get_api()

    vkLongpool = vk_api.longpoll.VkLongPoll(vkClient, wait=WAIT_TIME, preload_messages=True)

    tgClient.send_text("Бот запущен!")
    logger.info("Бот запущен!")
    
    while True:
        for event in vkLongpool.listen():
            handle(event, vkApi, tgClient)


def handle(event: vk_api.longpoll.Event, vkApi: vk_api.vk_api, tgClient: MyTelegram):
    try:
        vk.handle(event, vkApi, tgClient)

    except KeyboardInterrupt:
        raise
    
    except Exception as ex:
        ex_str = traceback.format_exc()
        error_str = "\n".join([f"Ошибка! {ex_str}", f'Event: {event!r}'])
        tgClient.send_text(error_str[-4090:])
        logger.error(error_str)
    

if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        main()
    except KeyboardInterrupt:
        log("Bot is stopped.")
            
    # exit(0)