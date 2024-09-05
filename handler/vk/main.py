from importlib import reload
from utils.my_classes import Message
from utils.database import get_tg_id, add_pair
from utils.config import CHATS_BLACKLIST
from vk_api.longpoll import VkEventType  # type: ignore[import-untyped]
import datetime

from ..telegram import MyTelegram
from . import functions as funcs
import vk_api.longpoll  # type: ignore[import-untyped]
import logging

from typing import Callable, TYPE_CHECKING


logger = logging.getLogger(__name__)
messages_cache: dict[tuple[str, str], str] = dict()
full_messages_cache: dict[tuple[str, str], dict] = dict()
binds_vk_to_tg: dict[int, int] = dict()


def handle(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: MyTelegram):
    if any([n in CHATS_BLACKLIST for n in [funcs.getConversationInfoByChatId(vkApi, event.chat_id)[0]]]):
        return
    
    if event.type == VkEventType.MESSAGE_NEW:
        import handler.vk as vk
        if not TYPE_CHECKING: vk = reload(vk)
        vk.main.handle_new_message(event, vkApi, tgClient)
        # handle_new_message(event, vkApi, tgClient)
    
    elif event.type == VkEventType.USER_TYPING_IN_CHAT:
        import handler.vk as vk
        if not TYPE_CHECKING: vk = reload(vk)
        vk.main.handle_user_typing(event, vkApi, tgClient)
        # handle_user_typing(event, vkApi, tgClient)
    
    elif event.type == VkEventType.MESSAGE_EDIT:
        import handler.vk as vk
        if not TYPE_CHECKING: vk = reload(vk)
        vk.main.handle_message_edit(event, vkApi, tgClient)
        # handle_message_edit(event, vkApi, tgClient)
    
    elif event.type in [VkEventType.READ_ALL_INCOMING_MESSAGES, VkEventType.MESSAGES_COUNTER_UPDATE, VkEventType.MESSAGE_FLAGS_RESET, VkEventType.MESSAGE_FLAGS_SET, 602]:
        pass
    
    else:
        import handler.vk as vk
        if not TYPE_CHECKING: vk = reload(vk)
        vk.main.handle_other_event(event, vkApi, tgClient)
        # handle_other_event(event, vkApi, tgClient)


def handle_message_edit(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: MyTelegram):    
    try:
        in_chat, mark = funcs.getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat, mark = None, None
    
    pair_for_dict = (event.peer_id, event.message_id)
    
    _previous_message = messages_cache.get(pair_for_dict)
    
    prep_time = f"[{datetime.datetime.fromtimestamp(event.timestamp).strftime('%H:%M:%S')}]"
    fromUser = funcs.getUserName(vkApi, event.user_id)
    print(", ".join(["{}:{}".format(n, getattr(event, n)) for n in dir(event) if n[0] !="_"]))

    string = f"{prep_time} {mark}[{in_chat} / {fromUser}] (ID:{event.message_id}): {event.message}\n * Прошлый текст был {repr(_previous_message) or '*неизвестно*'}"

    messages_cache[pair_for_dict] = event.message
    logger.info(string)
    
    if (tg_id := get_tg_id(event.message_id)):
        tgClient.reply_text(msg_id=int(tg_id), text=string)
    else:
        tgClient.send_text(string)


def handle_user_typing(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: MyTelegram):
    try:
        from_user = funcs.getUserName(vkApi, event.user_id) if getattr(event, "user_id", None) else None
    except vk_api.exceptions.ApiError:
        from_user = None
    
    try:
        in_chat, _ = funcs.getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat = None
    
    string = f"""В чате {in_chat!r} пишет {from_user!r}..."""
    logger.info(string)


def handle_other_event(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: MyTelegram):
    try:
        from_user = funcs.getUserName(vkApi, event.user_id) if getattr(event, "user_id", None) else None
    except vk_api.exceptions.ApiError:
        from_user = None
    
    try:
        in_chat, _ = funcs.getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat = None
        
    event_display_name = event.type.name if hasattr(event.type, 'name') else event.type
    
    event_all_args = ' | '.join(['event.{}: {}'.format(n, getattr(event, n)) for n in dir(event) if n[0]!='_' and bool(getattr(event, n))])  #  and not hasattr(event, "raw")
    # logging.info(f"{event.type.name}, {}")
    logger.info(f"{event_display_name}, {from_user=!r}, {in_chat=!r}, | {event_all_args} | ")


def _handle_new_message(event: vk_api.longpoll.Event, api: vk_api.vk_api.VkApiMethod, tg: MyTelegram):
    message: dict = api.messages.getById(message_ids=event.message_id)['items'][0]

    # logger.info("\n " + ", ".join
    #     (["{}: {}".format(n, getattr(message, n)) for n in dir(message) if n[0] != "_"])
    # )

    text, isInBlocklist = funcs.parse_message(message, api)
    logger.info(text)

    if isInBlocklist:
        return

    if (vk_id:=message.get('reply_message', {}).get('id')):
        msg = tg.reply_text(text=text, msg_id=get_tg_id(vk_id))
    else:
        msg = tg.send_text(text)
    
    if isinstance(msg, Message):
        binds_vk_to_tg[event.message_id] = msg.id
        add_pair(msg.id, event.message_id)
    else:
        print(f"Что-то пошло не так при отправке сообщения!\n{msg!r}")
    print(text)


def handle_new_message(event: vk_api.longpoll.Event, api: vk_api.vk_api.VkApiMethod, tg: MyTelegram):
    import handler.vk as vk
    if not TYPE_CHECKING: vk = reload(vk)
    vk.main._handle_new_message(event, api, tg)
    pair_for_dict = (event.peer_id, event.message_id)
    messages_cache[pair_for_dict] = event.message