from ..telegram_bot.classes import MyTelegram
from .handlers import (
    on_message_edit,
    on_message_new,
    on_message_react,
    on_message_read,
    on_flag_interacted,
    on_message_read_self,
    on_message_type,
    on_update_counter,
    on_other_event,
)
from utils.config import CHATS_BLACKLIST, Config
from utils.interface.vk_messages import get_tg_id
from vkbottle import API, UserPolling, Bot
from vkbottle_types.events.enums import UserEventType
from vkbottle_types.events.user_events import RawUserEvent
import logging


logger = logging.getLogger(__name__)


def get_old_messages(
    api: VkApiMethod,
    vk_longpoll: vk_api.longpoll.VkLongPoll,
    tg_client: MyTelegram,
) -> None:
    pass


def send_to_tg(tgClient: MyTelegram, text: str):
    BLOCK_SIZE = 4000
    blocks = [
        text[BLOCK_SIZE * i : BLOCK_SIZE * (i + 1)]
        for i in range(0, len(text) // BLOCK_SIZE)
    ]

    logger.debug(f"{blocks=}")
    for block in blocks:
        tgClient.send_text(f"<blockquote expandable>{block}</blockquote>")


async def main(chat_id: int):
    config = Config(chat_id)
    token = config._ACCESS_TOKEN
    # bot = Bot(token=token)
    # bot.on.message()()
    # bot.on.raw_event([i for i in UserEventType], RawUserEvent)()

    await bot.run_polling()
    ...
