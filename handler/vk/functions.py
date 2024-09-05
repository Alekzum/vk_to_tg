from utils.config import CHATS_BLACKLIST
from typing import Callable
import datetime
import vk_api  # type: ignore[import-untyped]

import logging


logger = logging.getLogger(__name__)

user_cache: dict[int, tuple[str, int]] = dict()
group_cache: dict[int, tuple[str, int]] = dict()
chat_cache: dict[int, tuple[str, int]] = dict()
conversation_cache: dict[int, tuple[tuple[str, str], int]] = dict()


def action_to_string(action: dict, api: vk_api.vk_api.VkApiMethod) -> str:
    translate_dict: dict[str, Callable[[dict, vk_api.vk_api.VkApiMethod], str]] = dict(
        chat_photo_update = lambda *_: "Обновил фото беседы",
        chat_photo_remove = lambda *_: "Убрал фото беседы",
        chat_create = lambda *_: "Создал беседу с названием «{action['text']}»",
        chat_title_update = lambda _action, _: f"Изменил название беседы на «{_action['text']}»",
        chat_invite_user = lambda _action, _api: f"Приглашен {_action.get('email', getUserName(_api, _action['member_id']))}",
        chat_kick_user = lambda _action, _api: f"Выгнан {_action.get('email', getUserName(_api, _action['member_id']))}",
        chat_pin_message = lambda *_: "Закрепил сообщение",
        chat_unpin_message = lambda *_: "Открепил сообщение",
        chat_invite_user_by_link = lambda *_: "Зашёл в беседу по ссылку",
    )

    _type = action['type']
    result_str: str = translate_dict.get(_type, lambda *_:f"""•Неизвестное действие "{_type}"•""")(action, api)
    
    return result_str


def get_url(obj: dict) -> tuple[str, str]:
    """Return media's url and this type"""
    _type = obj['type']

    translate_dict: dict[str, Callable[[dict], str|tuple[str, str]]] = dict(
        photo = lambda _obj:
            (
                [photik['url'] for photik in sorted(_obj[_type].get('sizes', []), key=lambda x: x['height'], reverse=True) if photik['type'] in ['w', 'z', 'x']]
            or [f"https://vk.com/photo{_obj[_type].get('owner_id', '???')}_{_obj[_type].get('id', '???')}"]
        )[0],

        video = lambda _obj: 
            _obj[_type]['url'],
        
        audio = lambda _obj: 
            _obj[_type]['url'],
        
        doc = lambda _obj: 
            (_obj[_type]['url'], f"{_obj[_type]['title']} (document)"),
        
        market = lambda _obj: 
            f"Артикул: {_obj[_type]['sku']}",
        
        market_album = lambda _obj: 
            f"Название: {_obj[_type]['title']}, id владельца: {_obj[_type]['owner_id']}",
        
        wall_reply = lambda _obj: 
            f"№{_obj[_type]['id']} от пользователя №{_obj[_type]['owner_id']}",
        
        sticker = lambda _obj: 
            _obj[_type]['images'][-1]['url'],
        
        gift = lambda _obj: 
            _obj[_type]['thumb_256'],
        
        audio_message = lambda _obj: 
            _obj[_type]['link_mp3'],
        
        wall = lambda _obj: 
            f"https://vk.com/wall{_obj[_type]['from_id']}_{_obj[_type]['id']}",
        
        link = lambda _obj: 
            _obj[_type]['url']
        
    )

    try:
        result_str: str | tuple[str, str] = translate_dict.get(_type, lambda _: f"""•Неизвестное вложение "{_type}"•""")(obj)
    except KeyError as ex:
        logger.error(f"Didn't get {ex.args[0]}. dir(obj)")
    
    if isinstance(result_str, str):
        result = (result_str, _type)

    elif isinstance(result_str, tuple):
        result = result_str
    
    return result


# User
def getUserName(api: vk_api.vk_api.VkApiMethod, user_id: int) -> str:
    global user_cache
    pair = user_cache.get(user_id)
    if pair is not None and pair[1] < 5:
        user_cache[user_id] = pair[0], pair[1]
        return pair[0]
    
    if user_id < 0:
        return getGroupName(api, abs(user_id))
    
    user = api.users.get(user_ids=user_id)[0]
    user_cache[user_id] = pair = (f"{user['first_name']} {user['last_name']}", 0)
    return pair[0]


# group
def getGroupName(api: vk_api.vk_api.VkApiMethod, group_id: int) -> str:
    global group_cache
    pair = group_cache.get(group_id)
    if pair is not None and pair[1] < 5:
        group_cache[group_id] = pair[0], pair[1] + 1
        return pair[0]
    
    group: dict = api.groups.getById(group_id=(abs(group_id)))[0]
    group_cache[group_id] = pair = group['name'], 0
    return pair[0]


# Chat
def getChatName(api: vk_api.vk_api.VkApiMethod, chat_id: int) -> str:
    global chat_cache
    pair = chat_cache.get(chat_id)
    if pair is not None and pair[1] < 5:
        chat_cache[chat_id] = pair[0], pair[1]+1
        return pair[0]
    
    chat = api.messages.getChatPreview(peer_id=chat_id)
    chat_cache[chat_id] = pair = (chat['preview']['title'], 0)
    return pair[0]


def getConversationInfo(api: vk_api.vk_api.VkApiMethod, message: dict) -> tuple[str, str]:
    conversation_id = message.get('peer_id')
    if conversation_id is None:
        return "*None*", ""

    global conversation_cache
    pair = conversation_cache.get(conversation_id)
    if pair is not None and pair[1] < 5:
        conversation_cache[conversation_id] = pair[0], pair[1] + 1
        return pair[0]

    if conversation_id > 2000000000:
        conversation = getChatName(api, conversation_id)
        mark = ""
    else:
        conversation = getUserName(api, conversation_id)
        mark = "[ЛС] "
    
    conversation_cache[conversation_id] = pair = ((conversation, mark), 0)
    return pair[0]


def getConversationInfoByChatId(api: vk_api.vk_api.VkApiMethod, peer_id: int) -> tuple[str, str]:
    """Return conversation's name and optional mark "[ЛС]" """
    conversation_id = int(f"2000000{peer_id}")
    
    global conversation_cache
    pair = conversation_cache.get(conversation_id)
    if pair is not None and pair[1] < 5:
        conversation_cache[conversation_id] = pair[0], pair[1] + 1
        return pair[0]

    if conversation_id > 2000000000:
        conversation = getChatName(api, conversation_id)
        mark = ""
    else:
        conversation = getUserName(api, conversation_id)
        mark = "[ЛС] "
    
    conversation_cache[conversation_id] = (conversation, mark), 0
    return conversation, mark


def getTextMessage(message: dict, api: vk_api.vk_api.VkApiMethod, only_text: bool = False) -> tuple[str, str]:
    text = message.get('text', "*нет текста*")

    to_add = []
    if (action:=message.get('action')):
        action_str = action_to_string(action, vk_api)
        to_add.append(action_str)
        del action, action_str
    
    if (attachments:=message.get('attachments', [])):
        for attachment in attachments:
            url, type_str = get_url(attachment)
            to_add.append(f"<a href='{url}'>{type_str}</a>")
        del attachments, attachment, url, type_str
    
    if not only_text:
        if (reply_to_message:=message.get("reply_message")):
            rtm = getTextMessage(reply_to_message, api, only_text=True)[0]
            rtmString = f"С ответом на сообщение:\n * {rtm}"
            to_add.append(rtmString)
            del reply_to_message, rtm, rtmString
        
        if (forwardedMessages:=message.get("fwd_messages")):
            fwdMsgs = [getTextMessage(fwdMsg, api, only_text=True)[0] for fwdMsg in forwardedMessages]
            fwdString = f"С пересланными сообщениями:{'\n * '.join([''] + fwdMsgs)}"
            to_add.append(fwdString)
            del forwardedMessages, fwdMsgs, fwdString
    
    to_add_string = "\n *".join(['']+to_add) if to_add else ""

    prep_time = f"[{datetime.datetime.fromtimestamp(message.get('date', 0)).strftime('%H:%M:%S')}]"

    user_ask = getUserName(api, message['from_id'])

    prep_text = text + to_add_string

    conversation, mark = getConversationInfo(api, message)

    info_conversation = f"{prep_time} {mark}[{conversation} / {user_ask}] (ID:{message['id']}): {prep_text}"
    return info_conversation, conversation


def parse_message(message: dict, api: vk_api.vk_api.VkApiMethod) -> tuple[str, bool]:
    """Return output and chatIsInBlocklist"""
    text, conversation = getTextMessage(message, api)
    isInBlocklist = conversation in CHATS_BLACKLIST
    return text, isInBlocklist