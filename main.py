from utils import runtime_platform, github
from utils.config import MyConfig
github.check_local_dir()
runtime_platform.check_platform()

if not github.restarted() or not runtime_platform.in_venv():
    exit(1)

import vk_api.longpoll as longpool   # type: ignore[import-untyped]

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


def send_to_tg(tgClient: MyTelegram, text: str):
    tgClient.send_text(f"<blockquote expandable>{text[:2000] + '...' + text[-2000:]}</blockquote>")


def save_ts_and_pts(vkLongpool: longpool.VkLongPoll, log=True):
    success = config.set("ts", vkLongpool.ts)
    if success is None:
        logger.warning("ключ \"ts\" не найден!")
    elif success and log:
        logger.info("сохранён ts")
    elif not success:
        logger.warning("не сохранён ts :\\")
    
    success = config.set("pts", vkLongpool.pts)
    if success is None:
        logger.warning("ключ \"pts\" не найден!")
    elif success and log:
        logger.info("сохранён pts")
    elif not success:
        logger.warning("не сохранён pts :\\")


def load_ts_and_pts(vkLongpool: longpool.VkLongPoll):
    ts, pts = config.get("ts"), config.get("pts")
    if ts is not None:
        vkLongpool.ts = ts
    if pts is not None:
        vkLongpool.pts = pts
    
    vkLongpool.update_longpoll_server(update_ts=False)


def main():
    tgClient = MyTelegram()
    vkClient = vk_api.VkApi(token=config.access_token)
    
    vkApi = vkClient.get_api()

    vkLongpool = longpool.VkLongPoll(
        vkClient, 
        wait=WAIT_TIME, 
        preload_messages=True,
        mode=sum([
            longpool.VkLongpollMode.GET_ATTACHMENTS, 
            longpool.VkLongpollMode.GET_PTS, 
            longpool.VkLongpollMode.GET_EXTENDED
        ])
    )
    
    load_ts_and_pts(vkLongpool)

    tgClient.send_text("Бот запущен!")
    logger.info("Бот запущен!")
    
    while True:
        try:
            for event in vkLongpool.listen():
                handle(event, vkApi, tgClient)
            save_ts_and_pts(vkLongpool, log=False)
        
        except KeyboardInterrupt:
            tgClient.stop()
            break
        
        except Exception as ex:
            ex_str = traceback.format_exc()
            # error_str = f"Ошибка! {ex_str}"
            error_str = f"{ex!r}\n{ex_str}"
            try:
                send_to_tg(tgClient, error_str)
            except Exception:
                pass
            logger.error(error_str + "\nОтправлено в тг")
    save_ts_and_pts(vkLongpool, log=True)


def handle(event: longpool.Event, vkApi: vk_api.vk_api, tgClient: MyTelegram):
    try:
        vk.handle(event, vkApi, tgClient)
    
    except Exception:
        ex_str = traceback.format_exc()
        # error_str = f"Ошибка! {ex_str}"
        error_str = ex_str
        send_to_tg(tgClient, error_str)
        send_to_tg(tgClient, f'Событие: {event!r}')
        logger.error(error_str)
    

if __name__ == "__main__":
    logger.info("Запуск бота...")
    try:
        main()
    except KeyboardInterrupt:
        log("Бот остановлен.")
    
    # exit(0)