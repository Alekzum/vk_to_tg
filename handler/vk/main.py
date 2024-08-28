from importlib import reload
from utils.my_classes import Message
from utils.database import get_tg_id, add_pair
from utils.config import CHATS_BLACKLIST
from vk_api.longpoll import VkEventType  # type: ignore[import-untyped]

from ..telegram import MyTelegram
from . import functions as funcs
import vk_api.longpoll  # type: ignore[import-untyped]
import logging

from typing import Callable, TYPE_CHECKING


logger = logging.getLogger(__name__)
messages_cache: dict[tuple[str, str], str] = dict()
binds_vk_to_tg: dict[int, int] = dict()


def handle(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: MyTelegram):
    if getattr(event, "chat_id", None) in CHATS_BLACKLIST:
        return
    
    if event.type == VkEventType.MESSAGE_NEW:
        handle_new_message(event, vkApi, tgClient)
    
    elif event.type == VkEventType.USER_TYPING_IN_CHAT:
        handle_user_typing(event, vkApi, tgClient)
    
    elif event.type == VkEventType.MESSAGE_EDIT:
        handle_message_edit(event, vkApi, tgClient)
    
    elif event.type in [VkEventType.READ_ALL_INCOMING_MESSAGES, VkEventType.MESSAGES_COUNTER_UPDATE, VkEventType.MESSAGE_FLAGS_RESET, VkEventType.MESSAGE_FLAGS_SET, 602]:
        pass
    
    else:
        handle_other_event(event, vkApi, tgClient)


def handle_message_edit(event: vk_api.longpoll.Event, vkApi: vk_api.VkApi, tgClient: MyTelegram):
    try:
        from_user = funcs.getUserName(vkApi, event.user_id) if getattr(event, "user_id", None) else None
    except vk_api.exceptions.ApiError:
        from_user = None
    
    try:
        in_chat, _ = funcs.getConversationInfoByChatId(vkApi, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat = None
    
    pair_for_dict = (event.peer_id, event.message_id)
    
    _previous_message = messages_cache.get(pair_for_dict)
    
    string = f"""In {in_chat!r} message from {from_user!r} (ID:{event.message_id}) edited from {_previous_message!r} to {event.message!r}"""
    messages_cache[pair_for_dict] = event.message
    logger.info(string)
    
    if (tg_id := get_tg_id(event.message_id)):
        tgClient.reply_text(int(tg_id), string)
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
    
    string = f"""In {in_chat!r} user {from_user!r} is typing..."""
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

    text, isInBlocklist = funcs.parse_message(message, api)
    logger.info(text)

    if isInBlocklist:
        return

    if (tg_id:=message.get('reply_message', {}).get('id')):
        msg = tg.reply_text(text=text, msg_id=int(tg_id))
    else:
        msg = tg.send_text(text)
    
    if isinstance(msg, Message):
        binds_vk_to_tg[event.message_id] = msg.id
        add_pair(msg.id, event.message_id)
    else:
        print("Something went wrong with sending messages!")
    print(text)


def handle_new_message(event, api, tg):
    import handler.vk as vk
    if not TYPE_CHECKING: vk = reload(vk)
    vk._handle_new_message(event, vkApi, tgClient)
    pair_for_dict = (event.peer_id, event.message_id)
    messages_cache[pair_for_dict] = event.message