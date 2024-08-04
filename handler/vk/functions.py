from utils.config import CHATS_BLACKLIST

from typing import Callable
import datetime
import vk_api


def _action_to_string(action: dict, api: vk_api.vk_api.VkApiMethod) -> str:
    translate_dict: dict[str, Callable[[dict, vk_api.vk_api.VkApiMethod], str]] = dict(
        chat_photo_update = lambda *_: "Обновил фото беседы",
        chat_photo_remove = lambda *_: "Убрал фото беседы",
        chat_create = lambda *_: "Создал беседу с названием «{action['text']}»",
        chat_title_update = lambda _action, _: f"Изменил название беседы на «{_action['text']}»",
        chat_invite_user = lambda _action, _api: f"Приглашен {_action.get('email', _getUserName(_api, _action['member_id']))}",
        chat_kick_user = lambda _action, _api: f"Выгнан {_action.get('email', _getUserName(_api, _action['member_id']))}",
        chat_pin_message = lambda *_: "Закрепил сообщение",
        chat_unpin_message = lambda *_: "Открепил сообщение",
        chat_invite_user_by_link = lambda *_: "Зашёл в беседу по ссылку",
    )

    _type = action['type']
    result_str: str = translate_dict.get(_type, lambda *_:f"""•Неизвестное действие "{_type}"•""")(action, api)
    
    return result_str


def _get_url(obj: dict) -> tuple[str, str]:
    """Return media's url and this type"""
    translate_dict: dict[str, Callable[[dict], str|tuple[str, str]]] = dict(
        photo=lambda _obj:(
            [photik['url'] for photik in sorted(_obj['photo'].get('sizes', []), key=lambda x: x['height'], reverse=True) if photik['type'] in ['w', 'z', 'x']]
            or [f"https://vk.com/photo{_obj['photo'].get('owner_id', '???')}_{_obj['photo'].get('id', '???')}"]
        )[0],
        video=lambda _obj: _obj['video']['url'],
        audio=lambda _obj: _obj['audio']['url'],
        doc=lambda _obj: (_obj['doc']['url'], f"{_obj['doc']['title']} (document)"),
        market=lambda _obj: f"Артикул: {_obj['market']['sku']}",
        market_album=lambda _obj: f"Название: {_obj['market_album']['title']}, id владельца: {_obj['market_album']['owner_id']}",
        wall_reply=lambda _obj: f"№{_obj['wall_reply']['id']} от пользователя №{_obj['wall_reply']['owner_id']}",
        sticker=lambda _obj: obj['sticker']['images'][-1]['url'],
        gift=lambda _obj: _obj['gift']['thumb_256'],
        audio_message=lambda _obj: _obj['audio_message']['link_mp3'],
        wall=lambda _obj: f"https://vk.com/wall{_obj['wall']['from_id']}_{_obj['wall']['id']}",
        link=lambda _obj: _obj['link']['url']
    )

    _type = obj['type']
    result_str: str | tuple[str, str] = translate_dict.get(_type, lambda _: f"""•Неизвестное вложение "{_type}"•""")(obj)
    
    if isinstance(result_str, str):
        result = (result_str, _type)

    elif isinstance(result_str, tuple):
        result = result_str
    
    return result


user_cache: dict[int, str] = dict()
group_cache: dict[int, str] = dict()
chat_cache: dict[int, str] = dict()
conversation_cache: dict[int, tuple[str, str]] = dict()

# User
def _getUserName(api: vk_api.vk_api.VkApiMethod, user_id: int) -> str:
    global user_cache
    user = user_cache.get(user_id)
    if user is None:
        if user_id < 0:
            return _getGroupName(api, abs(user_id))
        user_cache[user_id] = user
        user = api.users.get(user_ids=user_id)[0]
    return f"{user['first_name']} {user['last_name']}"


# group
def _getGroupName(api: vk_api.vk_api.VkApiMethod, group_id: int) -> str:
    global group_cache
    group = group_cache.get(group_id)
    if group is None:
        group = api.groups.getById(group_id=(abs(group_id)))[0]
        group_cache[group_id] = group
    return group['name']


# Chat
def _getChatName(api: vk_api.vk_api.VkApiMethod, chat_id: int) -> str:
    global chat_cache
    chat = chat_cache.get(chat_id)
    if chat is None:
        chat = api.messages.getChatPreview(peer_id=chat_id)
        chat_cache[chat_id] = chat
    return chat['preview']['title']


def _getConversationInfo(api: vk_api.vk_api.VkApiMethod, message: dict) -> tuple[str, str]:
    conversation_id = message.get('peer_id')
    if conversation_id is None:
        return "*None*", ""

    global conversation_cache
    pair = conversation_cache.get(conversation_id)
    if pair is not None:
        return pair

    if conversation_id > 2000000000:
        conversation = _getChatName(api, conversation_id)
        mark = ""
    else:
        conversation = _getUserName(api, conversation_id)
        mark = "[ЛС] "
    
    conversation_cache[conversation_id] = (conversation, mark)
    return conversation, mark


def _getConversationInfoByChatId(api: vk_api.vk_api.VkApiMethod, peer_id: int) -> tuple[str, str]:
    conversation_id = int(f"2000000{peer_id}")
    
    global conversation_cache
    pair = conversation_cache.get(conversation_id)
    if pair is not None:
        return pair

    if conversation_id > 2000000000:
        conversation = _getChatName(api, conversation_id)
        mark = ""
    else:
        conversation = _getUserName(api, conversation_id)
        mark = "[ЛС] "
    
    conversation_cache[conversation_id] = (conversation, mark)
    return conversation, mark


def _get_text_message(message: dict, api: vk_api.vk_api.VkApiMethod) -> tuple[str, str]:
    at = datetime.datetime.fromtimestamp(message.get('date')).strftime('%H:%M:%S')
    text = message.get('text')

    to_add = []
    if message.get('action'):
        action_str = _action_to_string(message['action'], vk_api)
        to_add.append(action_str)
        
    if len(message.get('attachments')) > 0:
        for attachment in message.get('attachments'):
            url, type_str = _get_url(attachment)
            to_add.append(f"<a href='{url}'>{type_str}</a>")
    
    to_add = ("\n *" + ", ".join(to_add)) if to_add else ""

    prep_time = f"[{at}] "

    user_ask = _getUserName(api, message['from_id'])

    prep_text = text + to_add

    conversation, mark = _getConversationInfo(api, message)

    info_conversation = f"{prep_time}{mark}[{conversation} / {user_ask}] (ID:{message['id']}): {prep_text}"
    return info_conversation, conversation


def _parse_message(message: dict, api: vk_api.vk_api.VkApiMethod) -> tuple[str, bool]:
    """Return output and chatIsInBlocklist"""
    text, conversation = _get_text_message(message, api)
    isInBlocklist = conversation in CHATS_BLACKLIST
    return text, isInBlocklist