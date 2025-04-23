from utils.config import CHATS_BLACKLIST
from .classes import Message, Attachment, ForwardMessage, ReplyMessage
from .utils import get_message_url, get_message_info
from typing import Callable, Any
from vk_api.vk_api import VkApiMethod  # type: ignore
import logging
import datetime


logger = logging.getLogger(__name__)

user_cache: dict[int, tuple[str, int]] = dict()
group_cache: dict[int, tuple[str, int]] = dict()
chat_cache: dict[int, tuple[str, int]] = dict()
conversation_cache: dict[int, tuple[tuple[str, str], int]] = dict()

nl = "\n"


def action_to_string(action: dict, api: VkApiMethod) -> str:
    translate_dict: dict[str, Callable[[dict, VkApiMethod], str]] = dict(
        chat_photo_update=lambda *_: "Обновил фото беседы",
        chat_photo_remove=lambda *_: "Убрал фото беседы",
        chat_create=lambda *_: "Создал беседу с названием «{action['text']}»",
        chat_title_update=lambda _action, _: f"Изменил название беседы на «{_action['text']}»",
        chat_invite_user=lambda _action, _api: f"Приглашен {_action.get('email', get_user_name(_api, _action['member_id']))}",
        chat_kick_user=lambda _action, _api: f"Выгнан {_action.get('email', get_user_name(_api, _action['member_id']))}",
        chat_pin_message=lambda _action, *_: f"Закрепил/а сообщение {_action['message']}",
        chat_unpin_message=lambda *_: "Открепил сообщение",
        chat_invite_user_by_link=lambda *_: "Зашёл в беседу по ссылку",
    )

    _type = action["type"]
    result_str: str = translate_dict.get(
        _type, lambda *_: f"""•Неизвестное действие "{_type}"•"""
    )(action, api)

    return result_str


def get_url(attach: Attachment) -> tuple[str, str]:
    """Return media's url and this type"""
    type_: str = attach.type
    media = attach.raw[type_]
    # media: dict[str, Any] = (
    #     (attach.media) if isinstance(attach.media, dict) else attach.media.__dict__
    # )

    translate_dict: dict[str, Callable[[], str | tuple[str, str]]] = dict(
        photo=lambda: (
            ((x := media.get("orig_photo", {}).get("url")) and [x])
            or [
                photo_["url"]
                for photo_ in sorted(
                    media.get("sizes", []), key=lambda x: x["height"], reverse=True
                )
                if photo_["type"] in ["w", "z", "x"]
            ]
            or [
                f"https://vk.com/photo{media.get('owner_id', '???')}_{media.get('id', '???')}"
            ]
        )[0],
        video=lambda: media.get("url", (media["player"], media["title"])),
        audio=lambda: media["url"],
        doc=lambda: (media["url"], f"{media['title']} (document)"),
        market=lambda: f"Артикул: {media['sku']}",
        market_album=lambda: f"Название: {media['title']}, id владельца: {media['owner_id']}",
        wall_reply=lambda: f"№{media['id']} от пользователя №{media['owner_id']}",
        sticker=lambda: media["images"][-1]["url"],
        gift=lambda: media["thumb_256"],
        audio_message=lambda: media["link_mp3"],
        wall=lambda: f"https://vk.com/wall{media['from_id']}_{media['id']}",
        link=lambda: media["url"],
    )

    default = lambda: ("", f"""•Неизвестное вложение {type_!r}•""")

    try:
        result_str: str | tuple[str, str] = translate_dict.get(type_, default)()
    except KeyError as ex:
        result_str = ("", f"""•Неизвестное вложение {type_!r}•""")
        logger.error(f"Didn't get {ex.args[0]}. {attach=}, {media=}")

    if isinstance(result_str, str):
        result = (result_str, type_)

    elif isinstance(result_str, tuple):
        result = result_str

    return result


def get_dialog_name(api: VkApiMethod, dialog_id: int) -> str:
    for f in (get_user_name, get_chat_name, get_group_name):
        try:
            r = f(api, dialog_id)
            if r is not None:
                return r
        except Exception:
            pass
    return "unknown"


# User
def get_user_name(api: VkApiMethod, user_id: int) -> str:
    global user_cache
    pair = user_cache.get(user_id)
    if pair is not None and pair[1] < 5:
        user_cache[user_id] = pair[0], pair[1]
        return pair[0]

    if user_id is not None and user_id < 0:
        return get_group_name(api, abs(user_id))

    user = api.users.get(user_ids=user_id)[0]
    user_cache[user_id] = pair = (f"{user['first_name']} {user['last_name']}", 0)
    return pair[0]


# group
def get_group_name(api: VkApiMethod, group_id: int) -> str:
    global group_cache
    pair = group_cache.get(group_id)
    if pair is not None and pair[1] < 5:
        group_cache[group_id] = pair[0], pair[1] + 1
        return pair[0]

    group: dict = api.groups.getById(group_id=(abs(group_id)))[0]
    group_cache[group_id] = pair = group["name"], 0
    return pair[0]


# Chat
def get_chat_name(api: VkApiMethod, ADMIN_IDS: int) -> str:
    global chat_cache
    pair = chat_cache.get(ADMIN_IDS)
    if pair is not None and pair[1] < 5:
        chat_cache[ADMIN_IDS] = pair[0], pair[1] + 1
        return pair[0]

    chat = api.messages.getChatPreview(peer_id=ADMIN_IDS)
    chat_cache[ADMIN_IDS] = pair = (chat["preview"]["title"], 0)
    return pair[0]


def get_conversation_info(api: VkApiMethod, item: Message | int) -> tuple[str, str]:
    if isinstance(item, Message):
        conversation_id = item.peer_id
    elif isinstance(item, int):
        conversation_id = item
    else:
        raise TypeError(f"Provide only Message or integer, not {item}!")

    global conversation_cache
    pair = conversation_cache.get(conversation_id)
    if pair is not None and pair[1] < 5:
        conversation_cache[conversation_id] = pair[0], pair[1] + 1
        return pair[0]

    conversation = get_dialog_name(api, conversation_id)
    if conversation_id > 2000000000:
        # conversation = get_chat_name(api, conversation_id)
        mark = ""
    else:
        # conversation = get_user_name(api, conversation_id)
        mark = "[ЛС] "

    conversation_cache[conversation_id] = pair = (conversation, mark), 0
    return pair[0]


def get_text_message(
    message: Message, api: VkApiMethod, text_depth: int
) -> tuple[str, str]:
    text = message.text or "*нет текста*"

    to_add = []
    if action := getattr(message, "action", None):
        action_str = action_to_string(action, api)
        to_add.append(action_str)
        del action, action_str

    if text_depth:
        check_attached_messages(message, to_add, api, text_depth)
    to_add.extend(check_attachments(message))

    if text_depth:
        msg_url = get_message_url(message)
        to_add.append(f'<a href="{msg_url}">сообщение</a>')
    to_add_string = "\n *".join([""] + to_add) if to_add else ""

    # msg_time = f"[{(message.date + datetime.timedelta(hours=4)):%H:%M:%S}]"
    # conversation, mark = get_conversation_info(api, message)
    time, string, conversation = get_message_info(message, api)
    msg_text = text + to_add_string

    # user_ask = get_user_name(api, message.from_id)

    # info_conversation = f"{msg_time} {mark}[{conversation} / {user_ask}]: {msg_text}"
    info_conversation = f"[{time}] {string}: {msg_text}"
    return info_conversation, conversation


def check_attachments(
    message: Message | ForwardMessage | ReplyMessage, to_add: list[str] | None = None
):
    """return something like ["&lt;a href='url'>something&lt;/a>", "&lt;a href='url'>something2&lt;/a>"]"""
    attachments = message.attachments
    to_add = to_add or list()
    tmp_list = list()
    for attachment in attachments:
        url, type_str = get_url(attachment)
        tmp_list.append(f"<a href='{url}'>{type_str}</a>")

    to_add.extend(tmp_list)
    return tmp_list


SEP = "\n *"


def parse_forwarded_messages(
    api: VkApiMethod, forwarded_messages: list[ForwardMessage], text_depth=3
) -> str:
    fwd_list: list[str] = []
    for fwd in forwarded_messages:
        tmp_list_: list[str] = list()
        attachments = check_attachments(fwd, tmp_list_)
        if (rtm := fwd.reply_message) and text_depth:
            fwd_str = parse_replied_message(api, rtm, text_depth=text_depth)
            attachments.extend(["С ответом на сообщение:"] + fwd_str.split(SEP))
        elif rtm:
            attachments.append([f"<a href='{rtm.link}'>Сообщение</a>"])

        if (fwd_msgs := fwd.forwarded_messages) and text_depth:
            fwd_str = parse_forwarded_messages(api, fwd_msgs, text_depth=text_depth - 1)
            attachments.extend(["С пересланными сообщениями:"] + fwd_str.split(SEP))

        elif fwd_msgs:
            attachments.append("С пересланными сообщениями...")

        attachments_str = SEP.join(attachments)
        user = get_user_name(api, fwd.from_id)

        fwd_list.append(f"{user}: {fwd.text}\n{attachments_str}")

    fwd_string = SEP.join([("\n" + fwd_).replace("\n", SEP) for fwd_ in fwd_list])
    return fwd_string


def parse_replied_message(
    api: VkApiMethod, reply_to_message: ReplyMessage, text_depth: bool | int = False
) -> str:
    reply_message_normal = Message(
        **api.messages.getById(message_ids=reply_to_message.id)["items"][0]
    )
    rtm = parse_message(
        reply_message_normal,
        api,
        text_depth=(0 if text_depth >= 0 else text_depth - 1),
    )[0]
    rtm_str = ("\n" + rtm).replace("\n", SEP)
    return rtm_str


def check_attached_messages(
    message: Message, to_add: list[str], api: VkApiMethod, text_depth: int
) -> None:
    if text_depth == 0:
        return

    if reply_to_message := message.reply_message:
        rtm_str = parse_replied_message(
            api,
            reply_to_message,
            text_depth=(1 if text_depth >= 0 else text_depth - 1),
        )
        rtm_string = f"С ответом на сообщение: {rtm_str}"
        to_add.append(rtm_string)

    if forwarded_messages := message.forwarded_messages:
        fwd_string = parse_forwarded_messages(
            api, forwarded_messages, text_depth=text_depth - 1
        )
        forwarded_string = f"С пересланными сообщениями: {fwd_string}"
        to_add.append(forwarded_string)


def parse_message(
    message: Message,
    api: VkApiMethod,
    # text_depth=3,
    text_depth=-1,
) -> tuple[str, bool]:
    """Return output and chat_is_in_blocklist"""
    msg = api.messages.getById(message_ids=message.id)["items"][0]
    message = Message(**msg)
    text, conversation = get_text_message(message, api, text_depth)
    is_in_blocklist = conversation in CHATS_BLACKLIST
    return text, is_in_blocklist
