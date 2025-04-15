from utils.interface.vk_messages import get_last_vk_id
from vkbottle import UserPolling, API
from utils.config import Config
import logging
import time

from requests.exceptions import ConnectionError, Timeout


logger = logging.getLogger(__name__)
TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError)
WAIT_TIME = 5


async def save_longpoll_info(chat_id: int, vk_longpoll: UserPolling, log=True):
    config = Config(chat_id)
    server = await vk_longpoll.get_server()
    if ts:=server.get("ts"):
        config._ts = ts

    if pts:=server.get("pts"):
        config._pts = pts
    
    config.save_values()


async def load_longpoll_info(chat_id: int, vk_longpoll: UserPolling):
    try:
        config = Config(chat_id)
    except KeyError:
        ts = 0
        pts = 0
    else:
        ts, pts = config._ts, config._pts
    
    if vk_longpoll.ts and ts is not None:
        vk_longpoll.ts = ts
    if vk_longpoll.pts and pts is not None:
        vk_longpoll.pts = pts

    vk_longpoll.update_longpoll_server(update_ts=False)


def get_longpoll(chat_id: int) -> tuple[API, UserPolling]:
    config = Config(chat_id)
    token = config._ACCESS_TOKEN
    vk_client = UserPolling(token=token)
    # vk_client = vk_api.VkApi(token=CONFIG.ACCESS_TOKEN)
    while True:
        try:
            vk_longpoll = longpoll.VkLongPoll(
                vk_client,
                wait=WAIT_TIME,
                preload_messages=True,
                mode=longpoll.VkLongpollMode.GET_ATTACHMENTS
                | longpoll.VkLongpollMode.GET_PTS
                | longpoll.VkLongpollMode.GET_RANDOM_ID,
            )
        except TIMEOUT_EXCEPTIONS as ex:
            logger.warning(f"No longpoll: Timeout")
            time.sleep(WAIT_TIME)
        except KeyError:
            raise
        except Exception as ex:
            logger.warning(f"No longpoll: {ex}")
            time.sleep(WAIT_TIME)
        else:
            break

    return vk_client, vk_longpoll
