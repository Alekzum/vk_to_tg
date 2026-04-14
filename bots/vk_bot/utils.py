from utils.interface.vk_interface import get_tg_id, get_vk_id, add_pair

# from utils.my_classes import TgMessage
# from utils.config import CHATS_BLACKLIST
from vk_api.longpoll import Event

from .classes import Message
from utils.my_logging import getLogger

from typing import Any
import json
import re


__all__ = ["get_tg_id", "get_vk_id", "add_pair"]
logger = getLogger(__name__)


URL_RE = re.compile(
    r"https?:\/\/(?:www\.)?"
    r"[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\b"
    r"(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)"
)


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
        logger.debug("printing...", object=obj)
    return string


def get_pair_for_dict(event: Event) -> tuple[int, int] | None:
    """Make key for dict from Event's peer_id + message_id or returns None if both of them not found

    Args:
        event (Event): event which contains peer+message ids

    Returns:
        tuple[int, int] | None: Result key
    """
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
        msg_id = thing.conversation_message_id
    elif isinstance(thing, Event):
        msg_id = thing.message_id
    else:
        raise TypeError(f"I dont know about {type(thing)}!")
    # return f"https://vk.com/im/convo/{peer_id}?cmid={msg_id}"
    return f"https://web.vk.me/convo/{peer_id}?cmid={msg_id}"


def find_first_message_media_url_index(text: str) -> int:
    links = URL_RE.findall(text)
    url = find_first_message_media_url(text)
    if not url:
        logger.debug("not found url...", links=links, url=url)
        return 0
        # logger.debug("not found url...", links=links, url=url)
    logger.debug("trying to links.index", links=links, url=url)
    return links.index(url)


def find_first_message_media_url(text: str) -> str:
    """For example
    ```[Time2] [Chat1 / User2]: text
    * With reply to message:<blockquote expandable>
    * [Time1] [Chat1 / User1]: *no text*
    *  * <a href="https://sun0-00.userapi.com/photo1">photo1</a>
    *  * <a href=""https://vk.com/doc1">document1</a>
    *  * <a href="https://web.vk.me/convo/CHAT_ID?cmid=CONVERSATION_MESSAGE_ID1">message</a></blockquote>
    * <a href="https://sun0-00.userapi.com/photo2">photo2</a>
    * <a href="https://web.vk.me/convo/CHAT_ID?cmid=CONVERSATION_MESSAGE_ID2">message</a>
    ```
    it's should be url to `photo2`
    """
    #
    links_in_msg = "\n".join(
        (x for x in text.splitlines() if x.strip().startswith("* <a"))
    )

    links = URL_RE.findall(links_in_msg)
    logger.debug("trying to links[0]", links=links)
    link = links[0] if links else ""
    return link
