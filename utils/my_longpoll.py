from utils.interface.vk_interface import get_last_vk_id
from utils.my_vk_api import AsyncVkApi, AsyncVkLongPoll, VkLongpollMode

# import vk_api.longpoll as longpoll
from utils.config import Config
import asyncio
from utils.my_logging import getLogger

from requests.exceptions import ConnectionError, Timeout


# MY_CONFIG = MyConfig(OWNER_ID)
logger = getLogger(__name__)
TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError)
WAIT_TIME = 10


async def save_longpoll_info(
    chat_id: int, ts: int | None = None, pts: int | None = None, log=True
):
    config = Config(chat_id)
    await config.load_values()

    if ts:
        config._ts = ts

    if pts:
        config._pts = pts

    await config.save_variables()


async def load_longpoll_info(
    chat_id: int, default_ts: int | None = None, default_pts: int | None = None
):
    try:
        config = Config(chat_id)
        await config.load_values()
    except KeyError:
        return default_ts, default_pts

    return config._ts, config._pts


async def get_client_and_longpoll(
    chat_id: int,
) -> tuple[AsyncVkApi, AsyncVkLongPoll]:
    logger = getLogger(__name__, chat_id=chat_id)
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
                mode=(
                    0
                    + VkLongpollMode.GET_ATTACHMENTS
                    + VkLongpollMode.GET_PTS
                    + VkLongpollMode.GET_RANDOM_ID
                ),
            )
            await vk_longpoll.update_longpoll_server()
        except TIMEOUT_EXCEPTIONS:
            logger.warning("No longpoll: Timeout")
            await asyncio.sleep(WAIT_TIME)
        except KeyError:
            raise
        except Exception as ex:
            logger.warning(f"No longpoll: {ex}", exc_info=True)
            raise ex
            # await asyncio.sleep(WAIT_TIME)
            break
        else:
            break

    return vk_client, vk_longpoll


__all__ = [
    "get_last_vk_id",
    "save_longpoll_info",
    "load_longpoll_info",
    "get_client_and_longpoll",
]
