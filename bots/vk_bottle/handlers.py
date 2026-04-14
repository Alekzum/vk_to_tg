from utils.my_logging import getLogger
from vkbottle_types.events.user_events import RawUserEvent
from vkbottle.user import Message
import json


def beautify_print(obj: object, indent: int | None = 4, need_to_print=True) -> str:
    string = json.dumps(
        obj,
        indent=indent,
        ensure_ascii=False,
        sort_keys=True,
        default=repr,
    )
    if need_to_print:
        logger.debug(string)
    return string


logger = getLogger(__name__)


def logger_info(string) -> None:
    logger.info(repr(string))
    print(string)


def logger_debug(string) -> None:
    logger.debug(repr(string))
    print(string)


async def new_message(message: Message):
    message.answer


async def raw_event(event: RawUserEvent):
    logger.debug("unknown event", event_object=event.object)
