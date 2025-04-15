from utils.my_classes import TgMessage
from utils.interface.vk_messages import get_tg_id, add_pair
from utils.config import CHATS_BLACKLIST
from vk_api.vk_api import VkApiMethod  # type: ignore
from vk_api.longpoll import Event
import vk_api.longpoll as longpoll  # type: ignore[import-untyped]
import datetime

from .. import telegram_bot
from . import my_functions as functions
from .classes import Message
import logging

from typing import Any
import vk_api
import json


logger = logging.getLogger(__name__)


def beautify_print(obj: Event | Any, indent: int | None = 4, need_to_print=True) -> str:
    string = json.dumps(
        obj,
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
        default=lambda x: (
            {i: getattr(x, i) for i in dir(x) if i[0] != "_"}
            if isinstance(x, Event)
            else repr(x)
        ),
    )
    if need_to_print:
        print(string)
    return string


def get_message_info(event: Event, api: VkApiMethod) -> tuple[str, str]:
    """time, other_string"""
    try:
        in_chat, mark = functions.get_conversation_info_by_chat_id(api, event.chat_id)
    except (vk_api.exceptions.ApiError, AttributeError):
        in_chat, mark = None, None

    prep_time = (
        (f"[{datetime.datetime.fromtimestamp(time) + datetime.timedelta(hours=4):%H:%M:%S}]")
        if (time := (event.timestamp if hasattr(event, "timestamp") else None))
        else "Unknown time"
    )
    sender_user = (
        functions.get_user_name(api, user_id)
        if (user_id := getattr(event, "user_id", None))
        else None
    )
    sender_group = (
        functions.get_group_name(api, group_id)
        if (group_id := getattr(event, "group_id", None))
        else None
    )
    sender = sender_user or sender_group or "*unknown*"
    
    r = f"{mark}[{in_chat} / {sender}] (ID:{event.message_id})"
    return prep_time, r


def get_message_string(event: Event, api: VkApiMethod) -> tuple[str, bool]:
    msg: dict = api.messages.getById(message_ids=event.message_id)["items"][0]
    message = Message(**msg)
    return functions.parse_message(message, api)


def get_pair_for_dict(event: longpoll.Event) -> tuple[int, int] | None:
    if (peer_id := (event.peer_id if hasattr(event, "peer_id") else None)) and (
        msg_id := (event.message_id if hasattr(event, "message_id") else None)
    ):
        return (peer_id, msg_id)
    return None


def get_from_user(
    api: VkApiMethod,
    event: Event,
    profiles: dict[int, dict] | None = None,
) -> Any | None:
    try:
        chat_id = getattr(event, "chat_id", 0)
        user = (profiles or {}).get(chat_id, None)
        if user:
            return user

        if not hasattr(event, "user_id"):
            return None
        try:
            return functions.get_user_name(api, getattr(event, "user_id", 0))
        except:
            return functions.get_user_name(api, getattr(event, "peer_id", 0))

    except vk_api.exceptions.ApiError:
        return None


def get_in_chat(
    api: VkApiMethod,
    event: longpoll.Event,
    conversations: dict[int, dict] | None = None,
    groups: dict[int, dict] | None = None,
) -> Any | None:
    def inner(chat_id: int):
        conversation = (conversations or {}).get(chat_id, None)
        if conversation:
            return conversation

        group = (groups or {}).get(chat_id, None)
        if group:
            return group
        return None

    try:
        chat_id = getattr(event, "chat_id", 0)
        if by_chat_id := inner(chat_id):
            return by_chat_id

        user_id = getattr(event, "user_id", 0)
        if by_user_id := inner(user_id):
            return by_user_id

        peer_id = getattr(event, "peer_id", 0)
        if by_peer_id := inner(peer_id):
            return by_peer_id
        return None

    except vk_api.exceptions.ApiError:
        return None
    # chat_id = event, "chat_id", event.peer_id if hasattr(event, "chat_id", getattr(event, "peer_id") else None)
    # try:
    #     in_chat_ = (conversations or {}).get(chat_id, (groups or {}).get(chat_id, None))
    #     if in_chat_ is not None:
    #         return in_chat_
    #     in_chat, _ = functions.get_conversation_info_by_chat_id(api, (event.peer_id if hasattr(event, "peer_id") else None))
    # except (vk_api.exceptions.ApiError, AttributeError, ValueError):
    #     in_chat = None
    # return in_chat


def get_from_peer(
    api: vk_api.vk_api.VkApiMethod,
    event: longpoll.Event,
    conversations: dict[int, dict] | None = None,
    groups: dict[int, dict] | None = None,
    profiles: dict[int, dict] | None = None,
):
    try:
        r = get_from_user(api, event, profiles)
    except:
        r = None
    return r or get_in_chat(api, event, conversations, groups)


def get_reactions(
    api: vk_api.vk_api.VkApiMethod,
) -> dict[int, str]:
    result = api.messages.getReactionsAssets()
    # print(result)
    assets = result["assets"]
    reactions = {emoji["reaction_id"]: emoji["links"]["static"] for emoji in assets}
    # exit()
    return reactions


def get_reaction(api: vk_api.vk_api.VkApiMethod, reaction_id: int, default="") -> str:
    """returns url to reaction"""
    reactions = get_reactions(api)
    return reactions.get(reaction_id, default)


def get_message_url(message: Message) -> str:
    return f"https://web.vk.me/convo/{message.peer_id}?cmid={message.id}"
