from utils.config import OWNER_ID
from utils.my_longpoll import (
    get_last_vk_id,
)

from requests.exceptions import ConnectionError, Timeout
from httpx import NetworkError, TimeoutException

from ..telegram_bot.classes import MyTelegram
from .utils import _add_handlers

from utils.config import Config

from utils.my_logging import getLogger
import asyncio
import vkbottle


logger = getLogger(__name__)
TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError, NetworkError, TimeoutException)


cache: dict[str, dict[tuple, dict]] = {
    "profiles_list_to_dict": {},
    "groups_list_to_dict": {},
    "conversations_list_to_dict": {},
}


def log(text: str) -> None:
    """like logger.info, but doesn't log via logger"""

    logger.debug(f"{text}")


async def send_to_tg(tgClient: MyTelegram, text: str):
    BLOCK_SIZE = 4000
    blocks = [
        text[BLOCK_SIZE * i : BLOCK_SIZE * (i + 1)]
        for i in range(0, len(text) // BLOCK_SIZE)
    ]

    logger.debug(f"{blocks=}")
    for block in blocks:
        await tgClient.send_text(f"<blockquote expandable>{block}</blockquote>")


async def get_old_messages(
    vk_bot: vkbottle.User,
    tg_client: MyTelegram,
) -> None:
    user_id = tg_client.CHAT_ID
    config = Config(user_id)
    await config.load_values()

    max_msg_id = await get_last_vk_id(user_id)
    result: dict = {"more": 1}

    index = 0
    kwargs = dict(
        ts=config.ts,
        pts=config.pts,
        lp_version=3,
        credentials=True,
        max_msg_id=max_msg_id,
    )
    while "more" in result and result["more"]:
        result = await vk_bot.api.request("messages.getLongPollHistory", kwargs)
        result = result["response"]

        # server = result["credentials"]["server"]
        ts = result["credentials"]["ts"]
        # key = result["credentials"]["key"]
        pts = result["new_pts"]

        history: list[list] = iter(result["history"].copy())  # lazy iterator

        for event in history:
            fake_event = event
            if event[0] in {4, 5}:  # new or edited message
                msgs_ = await vk_bot.api.request(
                    "messages.getById",
                    dict(message_ids=event[1]),  # get full message
                )
                msg_ = msgs_["response"]["items"]
                if not msg_:  # we dont found message, skip event 0-o
                    continue

                msg = msg_[0]

                # add timestamp and text fields
                to_new_event = event + [msg["date"], msg["text"]]
                fake_event = to_new_event
                # our fake event is ready for handling :stars:

            event = await vk_bot.polling.get_event(result["credentials"])

            await vk_bot.router.route(event, vk_bot.api)

            if tg_client.CHAT_ID == OWNER_ID:
                logger.debug(f"getLongPollHistory - {event=}, {fake_event=}")
            index += 1
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break

        config._set_ts(ts)
        config._set_pts(pts)
        await config.save_values()

        kwargs = dict(
            ts=config.ts,
            pts=config.pts,
            lp_version=3,
            credentials=True,
            max_msg_id=max_msg_id,
        )

    if index:
        logger.debug(f"{user_id=}, Processed {index} updates")


async def main(user_id: int):
    logger.debug(f"{user_id=}, Получение вк клиента и longpoll'а...")
    config = Config(user_id)
    await config.load_values()
    user_token = config._ACCESS_TOKEN

    vk_api = vkbottle.API(token=user_token)
    vk_polling = vkbottle.UserPolling(api=vk_api)
    vk_bot = vkbottle.User(api=vk_api, polling=vk_polling)

    tg_client = MyTelegram(user_id, name="VkBottle2TgBot")
    logger.debug(f"{user_id=}, Бот стартует...")
    await tg_client.init()

    if vk_polling.user_id is None:
        vk_polling.user_id = (await vk_api.request("users.get", {}))[
            "response"
        ][0]["id"]
    server = (
        await vk_api.request("messages.getLongPollServer", dict(need_pts=1))
    )["response"]

    server_ts, server_pts = server["ts"], server["pts"]
    logger.info(f"{user_id=}, On server: ts={server_ts}, pts={server_pts}")

    logger.info(f"{user_id=}, Saved: ts={config.ts}, pts={config.pts}")
    logger.info(
        f"{user_id=}, Bot is getting last {server_pts - config.pts} events"
    )
    await get_old_messages(vk_bot, tg_client)

    _add_handlers(vk_bot)
    # server_ts, server_pts = vk_longpoll.ts, vk_longpoll.pts
    # await set_polling_state(user_id, True)
    # await tg_client.send_text("Бот запущен!")
    # logger.info(f"{user_id=}, Бот запущен!")

    # while await get_polling_state(user_id):
    #     try:
    #         index = 0
    #         events = await vk_longpoll.check()
    #         for event in events:
    #             need_to_log = await handle(event, api, tg_client)
    #             if need_to_log:
    #                 index += 1
    #                 logger.debug(
    #                     f"{user_id=}, ts={vk_longpoll.ts}, pts={vk_longpoll.pts}"
    #                 )
    #             await asyncio.sleep(0)
    #         if index:
    #             await save_longpoll_info(user_id, vk_longpoll, log=False)
    #             logger.debug(f"{user_id=}, Processed {index} updates")
    #             if user_id == OWNER_ID:
    #                 logger.info(
    #                     f"{user_id=}, ts={vk_longpoll.ts}, pts={vk_longpoll.pts}"
    #                 )

    #     except KeyboardInterrupt:
    #         logger.info("set polling state to False")
    #         await set_polling_state(user_id, False)

    #     except TIMEOUT_EXCEPTIONS as ex:
    #         logger.warning("timeout")
    #         logger.debug(f"timeout, {ex=}")

    #     except Exception as ex:
    #         logger.warning(f"{ex=}")
    #         raise ex

    #     try:
    #         await asyncio.sleep(1)
    #     except asyncio.CancelledError:
    #         break

    # await tg_client.stop()

    # await save_longpoll_info(user_id, vk_longpoll, log=True)
    # logger.info(f"ts={vk_longpoll.ts}, pts={vk_longpoll.pts}")
