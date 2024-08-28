from typing import Callable, Any
from .config import CHATS_BLACKLIST
from .telegram import MyTelegram
from . import database
import vk_api.longpoll  # type: ignore[import-untyped]
import datetime
import logging
import vk_api


logger = logging.getLogger(__name__)


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
    result = user_cache.get(user_id)
    if result is None:
        if user_id < 0:
            return _getGroupName(api, abs(user_id))
        user = api.users.get(user_ids=user_id)[0]
        user_cache[user_id] = result = " ".join([n for n in [user.get('first_name'), user.get('last_name')] if n])
    
    return result


# group
def _getGroupName(api: vk_api.vk_api.VkApiMethod, group_id: int) -> str:
    global group_cache
    result = group_cache.get(group_id)
    if result is None:
        group = api.groups.getById(group_id=(abs(group_id)))[0]
        group_cache[group_id] = result = group['name']
    return result


# Chat
def _getChatName(api: vk_api.vk_api.VkApiMethod, chat_id: int) -> str:
    global chat_cache
    result = chat_cache.get(chat_id)
    if result is None:
        chat = api.messages.getChatPreview(peer_id=chat_id)
        chat_cache[chat_id] = result = chat['preview']['title']
    return result


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


def worker(event: vk_api.longpoll.Event, api: vk_api.vk_api.VkApiMethod, tg: MyTelegram):
    message = api.messages.getById(message_ids=event.message_id)['items'][0]

    text, isInBlocklist = _parse_message(message, api)
    logger.info(text)

    if isInBlocklist:
        return

    if 'reply_message' in message and (tg_id:=database.get_tg_id(message['reply_message']['id'])):
        msg = tg.reply_text(int(tg_id), text)
    else:
        msg = tg.send_text(text)
    
    if hasattr(msg, 'id'):
        database.add_pair(msg.id, event.message_id)
    print(text)

# def answer_to_message

def _parse_message(message: dict, api: vk_api.vk_api.VkApiMethod) -> tuple[str, bool]:
    """Return output and chatIsInBlocklist"""
    text, conversation = _message_to_string(message, api)
    isInBlocklist = conversation in CHATS_BLACKLIST
    return text, isInBlocklist


def _get_text_message(message: dict, api: vk_api.vk_api.VkApiMethod, _depth=0) -> tuple[str, str]:
    text = message.get('text', "")

    after_text_things = []
    if message.get('action'):
        action_str = _action_to_string(message['action'], vk_api)
        after_text_things.append(action_str)
    
    if (attachments:=message.get('attachments')):
        attachment_formatter = "<a href='{}'>{}</a>"
        attachments_list = [attachment_formatter.format(_get_url(attachment)) for attachment in attachments]
        attachments_string = ", ".join(attachments_list)
        after_text_things.append(attachments_string)
    
    if (fwd_messages := message.get("fwd_messages")) and _depth == 0:
        fwd_message_formatter = """{space}|{text}"""
        fwd_messages_list = [fwd_message_formatter.format(space="░"*(_depth+1), text=fwd_message) for fwd_message in fwd_messages]
        fwd_messages_string = "\n".join(fwd_messages_list)
        after_text_things.append(fwd_messages_string)
        # for fwd_message in fwd_messages:
        #     fwd_text = _get_text_message(fwd_message, api, _depth+1)
        #     forwarded_msg = f"""{"░"*(_depth+1)}│{forwarded_msg}"""


    elif (fwd_messages := message.get("fwd_messages")) and _depth != 0:
        fwd_message_formatter = """{space}|{text}"""
        fwd_messages_string = fwd_message_formatter.format(space="░"*(_depth+1), text="*пересланное сообщение*")
        after_text_things.append("")
    after_text_things_string = ("\n" + "\n".join(after_text_things)) if after_text_things else ""

    prep_text = text + after_text_things_string

    return prep_text


def _message_to_string(api, message):
    at = datetime.datetime.fromtimestamp(message.get('date')).strftime('%H:%M:%S')
    prep_time = f"[{at}] "

    prep_text = _get_text_message(api, message)
    user_ask = _getUserName(api, message['from_id'])
    conversation, mark = _getConversationInfo(api, message)

    info_conversation = f"{prep_time}{mark}[{conversation} / {user_ask}] (ID:{message['id']}): {prep_text}"
    return info_conversation, conversation