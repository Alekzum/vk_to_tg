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
WAIT_TIME = 5


def log(text: str) -> None:
    import datetime
    print(f"{str(datetime.datetime.now())[:-3]} - main.py - {text}")


def send_to_tg(tgClient: MyTelegram, text: str):
    tgClient.send_text(f"<blockquote expandable>{text[:2000] + '...' + text[-2000:]}</blockquote>")


def main():
    tgClient = MyTelegram()
    vkClient = vk_api.VkApi(token=config.access_token)
    
    vkApi = vkClient.get_api()

    vkLongpool = vk_api.longpoll.VkLongPoll(vkClient, wait=WAIT_TIME, preload_messages=True)

    tgClient.send_text("Бот запущен!")
    logger.info("Бот запущен!")
    
    while True:
        try:
            [handle(event, vkApi, tgClient) for event in vkLongpool.listen()] 
    
        except Exception as ex:
            ex_str = traceback.format_exc()
            # error_str = f"Ошибка! {ex_str}"
            error_str = ex_str
            send_to_tg(tgClient, error_str)
            logger.error(error_str + "\nSent to tg")


def handle(event: vk_api.longpoll.Event, vkApi: vk_api.vk_api, tgClient: MyTelegram):
    try:
        vk.handle(event, vkApi, tgClient)

    except KeyboardInterrupt:
        raise
    
    except Exception as ex:
        ex_str = traceback.format_exc()
        # error_str = f"Ошибка! {ex_str}"
        error_str = ex_str
        send_to_tg(tgClient, error_str)
        send_to_tg(tgClient, f'Event: {event!r}')
        logger.error(error_str)
    

if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        main()
    except KeyboardInterrupt:
        log("Bot is stopped.")
            
    # exit(0)