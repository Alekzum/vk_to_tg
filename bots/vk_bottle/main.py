from typing import NamedTuple

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
    user_id = tg_client.chat_id
    config = await Config.load_user_values(user_id)

    max_msg_id = await get_last_vk_id(user_id)
    index = 0
    while True:
        longpoll_history = await vk_bot.api.messages.get_long_poll_history(
            ts=config.ts,
            pts=config.pts,
            lp_version=3,
            credentials=True,
            max_msg_id=max_msg_id,
            extended=True,
        )
        assert longpoll_history.credentials
        assert longpoll_history.history
        assert longpoll_history.credentials.pts
        ts = longpoll_history.credentials.ts
        pts = longpoll_history.credentials.pts

        msg_ids = [
            int(event[1])
            for event in longpoll_history.history
            if event[0] == 4 or event[0] == 5
        ]
        msgs = {
            msg_id: msg
            for (msg_id, msg) in zip(
                msg_ids,
                (
                    await vk_bot.api.messages.get_by_id(message_ids=msg_ids)
                ).items,
            )
        }
        for event in longpoll_history.history:
            # fake_event = event
            # if event[0] in {4, 5}:  # new or edited message
            #     msg = msgs.get(int(event[1]))
            #     if msg is None:  # we dont found message, skip event 0-o
            #         continue

            #     # add timestamp and text fields
            #     fake_event = event + [msg.date, msg.text]
            #     # our fake event is ready for handling :stars:
            # else:
            #     event = await vk_bot.polling.get_event(
            #         longpoll_history.credentials.model_dump()
            #     )

            # await vk_bot.router.route(event, vk_bot.api)

            if tg_client.chat_id == OWNER_ID:
                logger.debug(f"getLongPollHistory - {event=}")
            index += 1
            try:
                await asyncio.sleep(0)
            except asyncio.CancelledError:
                break

        config.set_ts(ts)
        config.set_pts(pts)
        await config.save_variables()

        kwargs = dict(
            ts=config.ts,
            pts=config.pts,
            lp_version=3,
            credentials=True,
            max_msg_id=max_msg_id,
        )

    if index:
        logger.debug(f"{user_id=}, Processed {index} updates")


class BotPair(NamedTuple):
    vk: vkbottle.User
    tg: MyTelegram


async def get_bots(user_id: int) -> BotPair:
    tuple[vkbottle.User, MyTelegram]


async def main(user_id: int):
    logger = getLogger(__name__, user_id=user_id)
    logger.debug("Получение вк клиента и longpoll'а...")
    config = Config(user_id)
    await config.load_values()
    user_token = config._ACCESS_TOKEN

    vk_api = vkbottle.API(token=user_token)
    vk_polling = vkbottle.UserPolling(api=vk_api)
    vk_bot = vkbottle.User(api=vk_api, polling=vk_polling)

    tg_client = MyTelegram(user_id, name="VkBottle2TgBot")
    logger.debug("Бот стартует...")
    await tg_client.init()

    if vk_polling.user_id is None:
        vk_polling.user_id = (await vk_api.users.get())[0].id

    server = await vk_api.messages.get_long_poll_server(need_pts=1)
    assert server.pts, "need_pts=1 is used, but got pts=None!"

    server_ts, server_pts = server.ts, server.pts
    logger.info("On server", ts=server_ts, pts=server_pts)
    logger.info("Saved", ts=config.ts, pts=config.pts)

    logger.info("Bot is getting events", event_amount=(server_pts - config.pts))
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
