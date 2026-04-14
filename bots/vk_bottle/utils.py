from utils.my_logging import getLogger
from vkbottle.user import Message
from vkbottle_types.events.enums import UserEventType
from vkbottle_types.events.user_events import RawUserEvent
import vkbottle
from . import handlers


logger = getLogger(__name__)


def get_dict_key(message: Message) -> tuple[int, int] | None:
    peer_id: int | None = getattr(message, "peer_id", None)
    msg_id: int | None = getattr(message, "message_id", None)
    if peer_id and msg_id:
        return (peer_id, msg_id)
    return None


def get_message_url(thing: Message) -> str:
    logger.debug(f"{thing=}")
    peer_id = thing.peer_id
    if isinstance(thing, Message):
        msg_id = thing.id
    # elif isinstance(thing, Event):
    #     msg_id = thing.message_id
    else:
        raise TypeError(f"I dont know about {type(thing)}!")
    # return f"https://vk.com/im/convo/{peer_id}?cmid={msg_id}"
    return f"https://web.vk.me/convo/{peer_id}?cmid={msg_id}"


def _add_handlers(vk_bot: vkbottle.User) -> None:
    vk_bot.on.message()(handlers.new_message)
    vk_bot.on.raw_event(
        event=list(str(x) for x in UserEventType), dataclass=RawUserEvent
    )(handlers.raw_event)
