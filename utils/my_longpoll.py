from utils.interface.vk_messages import get_last_vk_id
from utils.my_vk_api import AsyncVkApi, AsyncVkLongPoll, VkLongpollMode

# import vk_api.longpoll as longpoll  # type: ignore[import-untyped]
from utils.config import Config
import asyncio
import structlog
from utils.my_logging import getLogger
import logging
import vk_api  # type: ignore
import time

from requests.exceptions import ConnectionError, Timeout


# MY_CONFIG = MyConfig(OWNER_ID)
logger = getLogger(__name__)
TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError)
WAIT_TIME = 5


async def save_longpoll_info(chat_id: int, vk_longpoll: AsyncVkLongPoll, log=True):
    config = Config(chat_id)
    await config.load_values()

    if vk_longpoll.ts:
        config._ts = vk_longpoll.ts

    if vk_longpoll.pts:
        config._pts = vk_longpoll.pts

    await config.save_values()


async def load_longpoll_info(chat_id: int, vk_longpoll: AsyncVkLongPoll):
    try:
        config = Config(chat_id)
        await config.load_values()
    except KeyError:
        ts = 0
        pts = 0
    else:
        ts, pts = config._ts, config._pts
    if vk_longpoll.ts and ts is not None:
        vk_longpoll.ts = ts
    if vk_longpoll.pts and pts is not None:
        vk_longpoll.pts = pts

    await vk_longpoll.update_longpoll_server(update_ts=False)


async def get_client_and_longpoll(chat_id: int) -> tuple[AsyncVkApi, AsyncVkLongPoll]:
    config = Config(chat_id)
    await config.load_values()
    token = config._ACCESS_TOKEN
    vk_client = AsyncVkApi(token=token)
    # vk_client = vk_api.VkApi(token=CONFIG.ACCESS_TOKEN)
    while True:
        try:
            vk_longpoll = AsyncVkLongPoll(
                vk_client,
                wait=WAIT_TIME,
                preload_messages=True,
                mode=(0
                    + VkLongpollMode.GET_ATTACHMENTS
                    + VkLongpollMode.GET_PTS
                    + VkLongpollMode.GET_RANDOM_ID
                ),
            )
            await vk_longpoll.update_longpoll_server()
        except TIMEOUT_EXCEPTIONS as ex:
            logger.warning(f"No longpoll: Timeout")
            await asyncio.sleep(WAIT_TIME)
        except KeyError:
            raise
        except Exception as ex:
            logger.warning(f"No longpoll: {ex}")
            await asyncio.sleep(WAIT_TIME)
        else:
            break

    return vk_client, vk_longpoll
