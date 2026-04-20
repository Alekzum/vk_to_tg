# meta
from abc import ABCMeta, abstractmethod
from typing import Iterable, Any, Protocol, Sequence

# vk_api
from utils.config import Config
from utils.my_vk_api import AsyncVkApi
from . import vk_api_classes

# functions
from typing import overload, Callable
from inspect import iscoroutinefunction

import structlog


def log_wrap(
    func: Callable,
) -> Callable:
    if not callable(func):
        raise ValueError(f"Excepted callable, not {type(func)}", func)

    def key_factory(args, kwargs):
        key_args = (args, kwargs)
        key_args_hash = hash(str(key_args))
        return key_args, key_args_hash

    async def inner_async(*args, **kwargs):
        key_args, key_args_hash = key_factory(args, kwargs)

        logger.debug(
            "calling async function",
            func=func,
            key_args=key_args,
            key_args_hash=key_args_hash,
        )
        try:
            result = await func(*args, **kwargs)
        except Exception:
            logger.exception(
                "Error when called func",
                func=func,
                key_args=key_args,
                key_args_hash=key_args_hash,
                exc_info=True,
            )
            raise
        else:
            logger.debug(
                "called function",
                func=func,
                key_args_hash=key_args_hash,
                result=result,
            )
            return result

    def inner_sync(*args, **kwargs):
        key_args, key_args_hash = key_factory(args, kwargs)

        logger.debug(
            "calling sync function",
            func=func,
            key_args=key_args,
            key_args_hash=key_args_hash,
        )
        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.exception(
                "Error when called func",
                func=func,
                key_args=key_args,
                key_args_hash=key_args_hash,
                exc_info=True,
            )
            raise
        else:
            logger.debug(
                "called function",
                func=func,
                key_args_hash=key_args_hash,
                result=result,
            )
            return result

    if iscoroutinefunction(func):
        return inner_async

    return inner_sync


class MessageMeta(Protocol):
    id: int


class VKApiMeta[MT = MessageMeta](metaclass=ABCMeta):
    user_id: int
    token: str

    @abstractmethod
    def __init__(self, user_id: int):
        self.get_conversation = log_wrap(self.get_conversation)
        self.get_message = log_wrap(self.get_message)
        self.get_group = log_wrap(self.get_group)
        self.get_user = log_wrap(self.get_user)
        self.get_chat = log_wrap(self.get_chat)
        self.get_peer = log_wrap(self.get_peer)

    @abstractmethod
    async def init(self) -> None: ...

    @abstractmethod
    async def get_conversation(self, peer_id: int) -> dict[str, Any] | None: ...

    @overload
    async def get_message(self, message_ids: int) -> MT: ...
    @overload
    async def get_message(self, message_ids: Iterable[int]) -> Sequence[MT]: ...
    @abstractmethod
    async def get_message(
        self, message_ids: int | Iterable[int]
    ) -> Sequence[MT] | MT: ...

    @abstractmethod
    async def get_group(self, group_id: int) -> str: ...
    @abstractmethod
    async def get_user(self, user_id: int) -> str: ...
    @abstractmethod
    async def get_chat(self, chat_id: int) -> str: ...
    async def get_peer(self, peer_id: int) -> str:
        return await get_dialog_name(self, peer_id)


class VKApi(VKApiMeta):
    def __init__(self, user_id: int) -> None:
        super().__init__(user_id)
        self.cfg = Config(user_id)
        self.token = ""

    async def init(self):
        await self.cfg.load_values()
        self.token = self.cfg._ACCESS_TOKEN
        self.api = AsyncVkApi(token=self.token)

    def _parse_message(self, raw) -> vk_api_classes.Message:
        return vk_api_classes.Message.model_validate(raw)  # pyright: ignore[reportReturnType]

    async def get_user(self, user_id: int) -> str:
        chat = await self.api.method("users.get", dict(user_ids=user_id))
        logger.debug("got raw user", user=chat)
        chat = chat[0]
        return " ".join(x for x in (chat["first_name"], chat["last_name"]) if x)

    async def get_chat(self, chat_id: int) -> str:
        chat = await self.api.method("messages.getChatPreview", dict(peer_id=chat_id))
        logger.debug("got raw chat", chat=chat)
        return chat["preview"]["title"]

    async def get_group(self, group_id: int) -> str:
        chat = await self.api.method("groups.getById", dict(group_ids=group_id))
        logger.debug("got raw group", group=chat)
        return chat[0]["name"]

    async def get_conversation(self, peer_id: int) -> dict[str, Any] | None:
        response = await self.api.method(
            "messages.getConversationsById",
            dict(peer_ids=peer_id),
        )
        conversation = response["items"][0] if response["items"] else None
        # if not conversation:
        #     raise ValueError(
        #         f"Didn't found conversation by id {peer_id}",
        #         peer_id,
        #     )
        return conversation

    @overload
    async def get_message(self, message_ids: int) -> vk_api_classes.Message: ...
    @overload
    async def get_message(
        self, message_ids: Iterable[int]
    ) -> Sequence[vk_api_classes.Message]: ...
    async def get_message(
        self, message_ids: int | Iterable[int]
    ) -> Sequence[vk_api_classes.Message] | vk_api_classes.Message:
        raw_msg_ids = (
            [message_ids] if isinstance(message_ids, int) else list(message_ids)
        )
        msg_ids = ",".join(str(x) for x in raw_msg_ids.copy())

        response = await self.api.method(
            "messages.getById",
            dict(message_ids=msg_ids, extended=1),
        )

        vk_messages = list(self._parse_message(x) for x in response["items"])
        if not isinstance(message_ids, int):
            return vk_messages

        vk_message = vk_messages[0] if vk_messages else None
        if not vk_message:
            raise ValueError(
                f"Didn't found message by {message_ids=}",
                message_ids,
            )
        return vk_message

    async def read_message(self, peer_id: int, message_id: int) -> bool:
        return await self.api.method(
            "messages.markAsRead",
            dict(peer_id=peer_id, start_message_id=message_id),
        )


class VKApiBottle(VKApiMeta):
    pass


async def get_dialog_name(api: VKApiMeta[Any], dialog_id: int) -> str:
    if not isinstance(dialog_id, int):
        raise TypeError(f"Excepted integer, not {type(dialog_id)}!")
    if dialog_id > 2000000000:
        return await api.get_chat(dialog_id)
    elif dialog_id > 0:
        return await api.get_user(dialog_id)
    return await api.get_group(dialog_id)


async def get_vk_api(user_id: int):
    api = VKApi(user_id=user_id)
    await api.init()
    return api


logger: structlog.typing.FilteringBoundLogger = structlog.get_logger(__name__)
