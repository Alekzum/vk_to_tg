from utils.interface.vk_messages import get_tg_id, get_vk_id, add_pair
from utils.my_classes import TgMessage
from utils.config import CHATS_BLACKLIST
from vk_api.longpoll import Event  # type: ignore

from .classes import Message
import structlog
from utils.my_logging import getLogger
import logging

from typing import Any
import vk_api  # type: ignore
import json


logger = getLogger(__name__)


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
        logger.debug(string)
    return string


def get_pair_for_dict(event: Event) -> tuple[int, int] | None:
    peer_id: int | None = getattr(event, "peer_id", None)
    msg_id: int | None = getattr(event, "message_id", None)
    if peer_id and msg_id:
        return (peer_id, msg_id)
    return None


# def get_reactions(
#     api: vk_api.vk_api.VkApiMethod,
# ) -> dict[int, str]:
#     result = api.messages.getReactionsAssets()
#     # logger.debug(result)
#     assets = result["assets"]
#     reactions = {emoji["reaction_id"]: emoji["links"]["static"] for emoji in assets}
#     # exit()
#     return reactions


# def get_reaction(api: vk_api.vk_api.VkApiMethod, reaction_id: int, default="") -> str:
#     """returns url to reaction"""
#     reactions = get_reactions(api)
#     return reactions.get(reaction_id, default)


def get_message_url(thing: Event | Message) -> str:
    logger.debug(f"{thing=}")
    peer_id = thing.peer_id
    if isinstance(thing, Message):
        msg_id = thing.id
    elif isinstance(thing, Event):
        msg_id = thing.message_id
    else:
        raise TypeError(f"I dont know about {type(thing)}!")
    # return f"https://vk.com/im/convo/{peer_id}?cmid={msg_id}"
    return f"https://web.vk.me/convo/{peer_id}?cmid={msg_id}"
