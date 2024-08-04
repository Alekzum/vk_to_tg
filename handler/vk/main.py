from utils.telegram import MyTelegram
from utils import database
from .functions import _parse_message
import vk_api.longpoll
import logging


logger = logging.getLogger(__name__)


def main(event: vk_api.longpoll.Event, api: vk_api.vk_api.VkApiMethod, tg: MyTelegram):
    message = api.messages.getById(message_ids=event.message_id)['items'][0]

    text, isInBlocklist = _parse_message(message, api)
    logger.info(text)

    if isInBlocklist:
        return

    if 'reply_message' in message and (tg_id:=database.get_tg_id(message['reply_message']['id'])):
        msg = tg.reply_text(text, int(tg_id))
    else:
        msg = tg.send_text(text)
    
    database.add_pair(msg.id, event.message_id)
    print(text)