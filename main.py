from importlib import reload

from utils.database import get_tg_id
from utils.config import CHATS_BLACKLIST

from requests.exceptions import ReadTimeout
from vk_api.longpoll import VkEventType
import vk_api.longpoll

import traceback
import logging
import vk_api
import utils


if not utils.runtime_platform.in_venv():
    exit(0)


config = utils.config.MyConfig()
logger = logging.getLogger(__name__)


def main():
    tgClient = utils.telegram.MyTelegram()
    vkClient = vk_api.VkApi(token=config.access_token)
    
    vkApi = vkClient.get_api()

    vkLongpool = vk_api.longpoll.VkLongPoll(vkClient, wait=5)

    tgClient.send_text("Бот запущен!")
    logger.info("Бот запущен!")
    
    while True:
        try:
            listen(vkLongpool, vkApi, tgClient)

        except KeyboardInterrupt:
            tgClient.stop()
            logger.info("Бот остановлен.")
            raise
            break


def listen(vkLongpool: vk_api.longpoll.VkLongPoll, vkApi: vk_api.VkApi, tgClient: utils.telegram.MyTelegram):
    try:
        for event in vkLongpool.listen():
            handle(event, vkApi, tgClient)

    except ReadTimeout:
        pass

    except KeyboardInterrupt:
        raise
    
    except Exception as ex:
        ex_str = traceback.format_exc()
        error_str = ("Ошибка!\n" + "\n".join(ex_str.splitlines()[-10:]))[:4095]
        tgClient.send_text(error_str)
        logger.error(f'\n{ex_str}\n')
        
    return


def handle(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: utils.telegram.MyTelegram):
    if getattr(event, "chat_id", None) in CHATS_BLACKLIST:
        return
    
    if event.type == VkEventType.MESSAGE_NEW:
        import handler.vk as vk
        vk = reload(vk)
        vk.main(event, vkApi, tgClient)
    
    elif event.type == VkEventType.USER_TYPING_IN_CHAT:
        handle_user_typing(event, vkApi, tgClient)
    
    elif event.type == VkEventType.MESSAGE_EDIT:
        handle_message_edit(event, vkApi, tgClient)
    
    elif event.type in [VkEventType.READ_ALL_INCOMING_MESSAGES, VkEventType.MESSAGES_COUNTER_UPDATE, VkEventType.MESSAGE_FLAGS_RESET, VkEventType.MESSAGE_FLAGS_SET, 602]:
        pass
    
    else:
        handle_other_event(event, vkApi, tgClient)


messages_cache: dict[tuple[str, str], str] = dict()

def handle_message_edit(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: utils.telegram.MyTelegram):
    try:
        from_user = utils.vk._getUserName(vkApi, event.user_id) if getattr(event, "user_id", None) else None
    except vk_api.exceptions.ApiError:
        from_user = None
    
    try:
        in_chat, _ = utils.vk._getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat = None
    
    pair_for_dict = (event.peer_id, event.message_id)
    
    _previous_message = messages_cache.get(pair_for_dict)
    previous_message = f"from {_previous_message} " if _previous_message is not None else ""
    
    string = f"""In {in_chat!r} message (ID:{event.message_id}) from {from_user!r} edited {previous_message!r}to {event.message!r}"""
    messages_cache[pair_for_dict] = event.message
    logger.info(string)
    
    if (tg_id := get_tg_id(event.message_id)):
        tgClient.reply_text(int(tg_id), string)
    else:
        tgClient.send_text(string)


def handle_user_typing(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: utils.telegram.MyTelegram):
    try:
        from_user = utils.vk._getUserName(vkApi, event.user_id) if getattr(event, "user_id", None) else None
    except vk_api.exceptions.ApiError:
        from_user = None
    
    try:
        in_chat, _ = utils.vk._getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat = None
    
    string = f"""In {in_chat!r} user {from_user!r} is typing..."""
    logger.info(string)


def handle_other_event(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: utils.telegram.MyTelegram):
    try:
        from_user = utils.vk._getUserName(vkApi, event.user_id) if getattr(event, "user_id", None) else None
    except vk_api.exceptions.ApiError:
        from_user = None
    
    try:
        in_chat, _ = utils.vk._getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat = None
        
    event_display_name = event.type.name if hasattr(event.type, 'name') else event.type
    
    event_all_args = ' | '.join(['event.{}: {}'.format(n, getattr(event, n)) for n in dir(event) if n[0]!='_' and bool(getattr(event, n))])  #  and not hasattr(event, "raw")
    # logging.info(f"{event.type.name}, {}")
    logger.info(f"{event_display_name}, {from_user=!r}, {in_chat=!r}\n\t| {event_all_args} | ")
    

if __name__ == "__main__":
    logger.info("Запуск бота...")
    started = True
    while started:
        try:
            main()
        except KeyboardInterrupt:
            started = False
        except Exception:
            pass
            
    # exit(0)