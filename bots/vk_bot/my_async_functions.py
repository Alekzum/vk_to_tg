from utils.config import CHATS_BLACKLIST
from utils.my_vk_api import VkApiMethod
from .classes import Message, Attachment, ForwardMessage, ReplyMessage
from .classes.messages import MessageAction, MessageActionType
from .utils import get_message_url
from vk_api.longpoll import Event  # type: ignore[import-untyped]
from vk_api.exceptions import ApiError  # type: ignore[import-untyped]
from abc import abstractmethod
from typing import Callable, Awaitable, Literal, Any, overload
from pydantic import BaseModel, Field
from urllib.parse import quote
import structlog
from utils.my_logging import getLogger
import logging
import pathlib
import pickle


class CacheItem(BaseModel):
    name: str
    TTL: int = 5


class MemoryCache(BaseModel):
    items: dict[int, CacheItem] = Field(default_factory=lambda: dict())

    @abstractmethod
    def update(self, id: int, name: str) -> None: ...
    @abstractmethod
    async def get(self, api: VkApiMethod, id: int) -> str: ...
    @abstractmethod
    async def update_info(self, api: VkApiMethod, id: int) -> tuple[bool, str]: ...


class CacheLambda(MemoryCache):
    api_method: str
    api_args: Callable[[int], dict[str, Any]]
    result_parser: Callable[[dict[str, Any]], str]

    def update(self, id: int, name: str, TTL=5) -> None:
        self.items[id] = CacheItem(name=name, TTL=TTL)

    async def update_info(
        self, api: VkApiMethod, id: int, _return=False
    ) -> tuple[bool, str]:
        kwargs = self.api_args(id)
        try:
            raw_info = await api._vk.method(self.api_method, values=kwargs)
            logger.debug(f"{self.api_method=}, {id=}, {raw_info=}")
            checked_info = raw_info[0] if isinstance(raw_info, list) else raw_info
            info = self.result_parser(checked_info)
            self.update(id=id, name=info, TTL=5)
            return True, info
        except Exception as ex_:
            ex = ex_

        if _return:
            # logger.warning(f"{id=}, {self.api_method=}, {self.api_args(id)=}, {ex=}")
            info = f"*unknown* (id: {id})"
            return False, info

        if abs(id) == id:
            info = f"*unknown* (id: {id})"
            return False, info

        status, temp = await self.update_info(api, abs(id), _return=True)

        if status:
            return True, temp
        else:
            logger.warning(
                f"{id=}, {self.api_method=}, {self.api_args(id)=}, {ex=}, also tried with {abs(id)=}"
            )
            info = f"*unknown* (id: {id})"
            return False, info

    async def get(self, api: VkApiMethod, id: int) -> str:
        item = self.items.get(id)
        if item is None or item.TTL <= 0:
            try:
                status, temp = await self.update_info(api, id)
                logger.debug(
                    f"{id=}, {self.api_method=}, {self.api_args(id)=}, {temp=}"
                )
                return temp
            except Exception as ex:
                logger.error(f"{id=}, {self.api_method=}, {self.api_args(id)=}, {ex=}")
                raise ex
        self.update(id=id, name=item.name, TTL=item.TTL - 1)
        return item.name


class Caches(BaseModel):
    caches_file: pathlib.Path = Field(
        default_factory=lambda: pathlib.Path(__file__).parent.joinpath(
            "data", "cache_async_functions.pkl"
        )
    )
    user_cache: MemoryCache
    group_cache: MemoryCache
    chat_cache: MemoryCache

    @classmethod
    def _create_new(cls):
        return cls(
            user_cache=CacheLambda(
                items=dict(),
                api_method="users.get",
                api_args=lambda id: dict(user_ids=id),
                result_parser=lambda d: " ".join([d["first_name"], d["last_name"]]),
            ),
            group_cache=CacheLambda(
                items=dict(),
                api_method="groups.getById",
                api_args=lambda id: dict(group_ids=abs(id)),
                result_parser=lambda d: d["name"],
            ),
            chat_cache=CacheLambda(
                items=dict(),
                api_method="messages.getChatPreview",
                api_args=lambda id: dict(peer_id=id),
                result_parser=lambda d: d["preview"]["title"],
            ),
        )

    @classmethod
    def load_cache(cls):
        tmp = cls._create_new()
        cache_file = tmp.caches_file
        if not cache_file.parent.exists():
            cache_file.parent.mkdir()
        if not cache_file.exists():
            cache_file.write_bytes(b"")

        raw = cache_file.read_bytes()
        if not raw:
            return tmp

        obj = pickle.loads(raw)
        return obj

    def save_cache(self):
        cache_file = self.caches_file
        raw = pickle.dumps(self)
        cache_file.write_bytes(raw)

    def __del__(self):
        self.save_cache()


logger = getLogger(__name__)

nl = "\n"
caches: Caches = Caches.load_cache()


async def get_message_info(
    message: Message, api: VkApiMethod, include_msg_id=False
) -> tuple[str, str, str]:
    """returns: time, other_string, conservation's name

    f"[{time}] {other_string}"
    """

    peer_id = message.peer_id
    sender_id = message.from_id

    if peer_id > 2000000000:
        mark = ""
    elif peer_id > 0:
        mark = "[ЛС] "
    else:
        mark = ""
    if peer_id > 2000000000:
        mark = ""
    else:
        mark = "[ЛС] "

    try:
        chat = await get_dialog_name(api, peer_id)
    except ApiError as ex:
        logger.warning(f"catch {ex}")
        chat = "*unknown*"

    prep_time = f"{message.date:%d.%m.%y, %H:%M:%S}" or "Unknown time"

    sender = await get_dialog_name(api, sender_id)
    text = f"{mark}[{chat} / {sender}]" + (
        " (ID:{event.message_id})" if include_msg_id else ""
    )
    return prep_time, text, chat


async def action_to_string(action: MessageAction, api: VkApiMethod) -> str:
    async def chat_photo_update(_action: MessageAction, _api: VkApiMethod):
        return "Обновил фото беседы"

    async def chat_photo_remove(_action: MessageAction, _api: VkApiMethod):
        return "Убрал фото беседы"

    async def chat_create(_action: MessageAction, _api: VkApiMethod):
        return f"Создал беседу с названием «{action.text}»"

    async def chat_title_update(_action: MessageAction, _api: VkApiMethod):
        return f"Изменил название беседы на «{_action.text}»"

    async def chat_invite_user(_action: MessageAction, _api: VkApiMethod):
        # assert _action == MessageActionType()
        return f"Приглашен {_action.email or await get_user_name(_api, _action.member_id)}"  # type: ignore[arg-type]

    async def chat_kick_user(_action: MessageAction, _api: VkApiMethod):
        return f"Выгнан {_action.email or await get_user_name(_api, _action.member_id)}"  # type: ignore[arg-type]

    async def chat_pin_message(_action: MessageAction, _api: VkApiMethod):
        return f"Закрепил/а сообщение {_action.message}"

    async def chat_unpin_message(_action: MessageAction, _api: VkApiMethod):
        return "Открепил сообщение"

    async def chat_invite_user_by_link(_action: MessageAction, _api: VkApiMethod):
        return "Зашёл в беседу по ссылку"

    async def default(_action: MessageAction, _api: VkApiMethod):
        return f"""•Неизвестное действие "{_type}"•"""

    # translate_dict: dict[str, Callable[[dict, VkApiMethod], Awaitable[str]]] = dict(
    #     chat_photo_update=chat_photo_update,
    #     chat_photo_remove=chat_photo_remove,
    #     chat_create=chat_create,
    #     chat_title_update=chat_title_update,
    #     chat_invite_user=chat_invite_user,
    #     chat_kick_user=chat_kick_user,
    #     chat_pin_message=chat_pin_message,
    #     chat_unpin_message=chat_unpin_message,
    #     chat_invite_user_by_link=chat_invite_user_by_link,
    # )

    translate_dict: dict[
        MessageActionType, Callable[[MessageAction, VkApiMethod], Awaitable[str]]
    ] = {
        MessageActionType.CHAT_PHOTO_UPDATE: chat_photo_update,
        MessageActionType.CHAT_PHOTO_REMOVE: chat_photo_remove,
        MessageActionType.CHAT_CREATE: chat_create,
        MessageActionType.CHAT_TITLE_UPDATE: chat_title_update,
        MessageActionType.CHAT_INVITE_USER: chat_invite_user,
        MessageActionType.CHAT_KICK_USER: chat_kick_user,
        MessageActionType.CHAT_PIN_MESSAGE: chat_pin_message,
        MessageActionType.CHAT_UNPIN_MESSAGE: chat_unpin_message,
        MessageActionType.CHAT_INVITE_USER_BY_LINK: chat_invite_user_by_link,
    }

    _type = action.type
    result_str: str = await translate_dict.get(_type, default)(action, api)

    return result_str


def get_attachment_info(attachment: Attachment) -> tuple[str, str]:
    """Return media's url and this type"""

    def russify_attachment(attachment_info: tuple[str, str]) -> tuple[str, str]:
        # logger.info(f"{attachment_info = }")
        attachment_url, attachment_type = attachment_info
        converting: dict[str, dict[str, str] | str] = dict(
            photo="фото",
            video="видео",
            audio="аудио",
            audio_message="голосовое сообщение",
            doc="документ",
            link="ссылка",
            market="товар",
            market_album="подборка товаров",
            wall="запись на стене",
            wall_reply="комментарий на стене",
            sticker="стикер",
            gift="подарок",
            call=dict(
                video="видео-звонок",
                audio="звонок",
                canceled_by_initiator="завершён инициатором на этапе дозвона",
                canceled_by_receiver="завершён получателем на этапе дозвона",
                reached="состоялся и завершён любой стороной",
            ),
        )
        type_rus = converting.get(
            attachment_type.split(" ")[0], attachment_type.split(" ")[0]
        )

        # logger.info(f"{type_rus = }")
        if isinstance(type_rus, str):
            convert_dict = dict(attachment_type=type_rus)
        else:
            convert_dict = type_rus

        type_rus = " ".join(
            x for i in attachment_type.split(" ") if (x := convert_dict.get(i, i))
        )

        # logger.info(f"after invoking{type_rus = }")
        return attachment_url, type_rus

        # attachment_url, attachment_type = attachment_info
        # converting: dict[str, Callable[[], str] | str] = dict(
        #     photo="фото",
        #     video="видео",
        #     audio="аудио",
        #     audio_message="голосовое сообщение",
        #     doc="документ",
        #     link="ссылка",
        #     market="товар",
        #     market_album="подборка товаров",
        #     wall="запись на стене",
        #     wall_reply="комментарий на стене",
        #     sticker="стикер",
        #     gift="подарок",
        #     call=lambda: " ".join(
        #         x
        #         for i in attachment_type.split(" ")
        #         if (
        #             x := dict(
        #                 video="видео-звонок",
        #                 audio="звонок",
        #                 canceled_by_initiator="завершён инициатором на этапе дозвона",
        #                 canceled_by_receiver="завершён получателем на этапе дозвона",
        #                 reached="состоялся и завершён любой стороной",
        #             ).get(i, "")
        #         )
        #     ),
        # )
        # type_rus = converting[attachment_type.split(" ")[0]]
        # if not isinstance(type_rus, str):
        #     type_rus = type_rus()
        # return attachment_url, type_rus

    attachment_type: str = attachment.type
    media: dict = attachment.raw[attachment_type]

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
        # sticker=lambda: media.get("animation_url", media["images"][-1]["url"]),
        sticker=lambda: media["images"][-1]["url"],
        gift=lambda: media["thumb_256"],
        audio_message=lambda: media["link_mp3"],
        wall=lambda: f"https://vk.com/wall{media['from_id']}_{media['id']}",
        link=lambda: media["url"],
        call=lambda: (
            "",
            " ".join(
                (
                    i
                    for i in [
                        "call",
                        media["video"] and "video" or "audio",
                        media["state"],
                    ]
                    if i
                )
            ),
        ),
    )
    translate_dict["audio-message"] = lambda: (
        (r[0] if isinstance(r := translate_dict["audio_message"](), tuple) else r),
        "audio_message",
    )
    translate_dict["gift-item"] = lambda: (
        (r[0] if isinstance(r := translate_dict["gift"](), tuple) else r),
        "gift",
    )
    # .update(
    #     {
    #         "gift-item": lambda: (translate_dict["gift"](), "gift"),
    #         "audio-message": translate_dict["audio_message"]
    #     }
    # )

    default = lambda: ("", f"""•Неизвестное вложение {attachment_type!r}•""")

    try:
        result_str: str | tuple[str, str] = translate_dict.get(
            attachment_type, default
        )()
    except KeyError as ex:
        result_str = ("", f"""•Неизвестное вложение {attachment_type!r}•""")
        logger.error(f"Didn't get {ex.args[0]}. {attachment=}, {media=}")

    if isinstance(result_str, str):
        result = (result_str, attachment_type)

    elif isinstance(result_str, tuple):
        result = result_str

    result = russify_attachment(result)
    return result


# User
async def get_user_name(api: VkApiMethod, user_id: int) -> str:
    return await caches.user_cache.get(api, user_id)


# group
async def get_group_name(api: VkApiMethod, group_id: int) -> str:
    return await caches.group_cache.get(api, group_id)


# Chat
async def get_chat_name(api: VkApiMethod, chat_id: int) -> str:
    return await caches.chat_cache.get(api, chat_id)


# async def get_dialog_name(
#     api: VkApiMethod,
#     dialog_id: int,
#     dialog_type: Literal["chat", "user", "group"] | None = None,
# ) -> str:
#     if dialog_type == "user":
#         return await get_user_name(api, dialog_id)
#     elif dialog_type == "chat":
#         return await get_chat_name(api, dialog_id)
#     elif dialog_type == "group":
#         return await get_group_name(api, dialog_id)

#     if dialog_id > 2000000000:
#         return await get_chat_name(api, dialog_id)
#         mark = ""
#     else:
#         return await get_user_name(api, dialog_id)

#     # for f in (get_user_name, get_chat_name, get_group_name):
#     #     try:
#     #         r = await f(api, dialog_id)
#     #         if r is not None:
#     #             return r
#     #     except Exception:
#     #         pass
#     # return "unknown"


@overload
async def get_dialog_name(api: VkApiMethod, dialog_id: Message | int) -> str: ...
@overload
async def get_dialog_name(
    api: VkApiMethod, dialog_id: Message | int, dialog_type: None
) -> str: ...
@overload
async def get_dialog_name(
    api: VkApiMethod,
    dialog_id: Message | int,
    dialog_type: Literal["chat", "user", "group"],
) -> str: ...
async def get_dialog_name(
    api: VkApiMethod,
    dialog_id: Message | int,
    dialog_type: Literal["chat", "user", "group"] | None = None,
) -> str:
    if isinstance(dialog_id, Message):
        conversation_id = dialog_id.peer_id
    elif isinstance(dialog_id, int):
        conversation_id = dialog_id
    else:
        raise TypeError(f"Provide only Message or integer, not {dialog_id}!")

    if dialog_type:
        if dialog_type == "user":
            return await get_user_name(api, conversation_id)
        elif dialog_type == "chat":
            return await get_chat_name(api, conversation_id)
        elif dialog_type == "group":
            return await get_group_name(api, conversation_id)

    if conversation_id > 2000000000:
        conversation = await get_chat_name(api, conversation_id)
        logger.debug(f"{conversation_id=}, chat: {conversation}")
        # mark = ""
    elif conversation_id > 0:
        conversation = await get_user_name(api, conversation_id)
        logger.debug(f"{conversation_id=}, private_chat: {conversation}")
        # mark = "[ЛС] "
    else:
        conversation = await get_group_name(api, conversation_id)
        logger.debug(f"{conversation_id=}, group: {conversation}")
        # mark = ""

    # return conversation, mark
    return conversation


async def get_text_message(
    message: Message, api: VkApiMethod, text_depth: int
) -> tuple[str, str]:
    """Return f"[{time}] {msg_data}: {msg_text}" and conversation's title"""
    text = message.text or "*нет текста*"

    to_add = []
    action: None | MessageAction = getattr(message, "action", None)
    if action:
        action_str = await action_to_string(action, api)
        to_add.append(action_str)
        del action, action_str

    if text_depth:
        await check_attached_messages(message, to_add, api, text_depth)
    to_add.extend(check_attachments(message))

    if text_depth:
        msg_url = get_message_url(message)
        to_add.append(f'<a href="{msg_url}">сообщение</a>')
    to_add_string = "\n * ".join([""] + to_add) if to_add else ""

    time, string, conversation = await get_message_info(message, api)
    msg_text = text + to_add_string

    # user_ask = await get_user_name(api, message.from_id)

    # info_conversation = f"{msg_time} {mark}[{conversation} / {user_ask}]: {msg_text}"
    info_conversation = f"[{time}] {string}: {msg_text}"
    return info_conversation, conversation


def check_attachments(
    message: Message | ForwardMessage | ReplyMessage, to_add: list[str] | None = None
):
    """return something like ["&lt;a href="url">something&lt;/a>", "&lt;a href="url">something2&lt;/a>"]"""
    attachments = message.attachments
    to_add = to_add or list()
    tmp_list = list()
    for attachment in attachments:
        url, type_str = get_attachment_info(attachment)
        tmp_list.append(f'<a href="{url}">{type_str}</a>' if url else type_str)
        # if url:
        #     tmp_list.append(f'!test! <a href="{url}">{type_str}</a>')
        # tmp_list.append(f"{type_str}: {url}" if url else type_str)

    to_add.extend(tmp_list)
    return tmp_list


SEP = "\n * "


async def parse_forwarded_messages(
    api: VkApiMethod, forwarded_messages: list[ForwardMessage], text_depth=3
) -> str:
    fwd_list: list[str] = []
    for fwd in forwarded_messages:
        tmp_list_: list[str] = list()
        attachments = check_attachments(fwd, tmp_list_)
        if (rtm := fwd.reply_message) and text_depth:
            rtm_str = await parse_replied_message(api, rtm, text_depth=text_depth)
            attachments.append(
                f"С ответом на сообщение:<blockquote expandable>{rtm_str.replace(SEP, "\n | ")}</blockquote>"
            )
        elif rtm:
            attachments.append([f'<a href="{rtm.link}">Сообщение</a>'])

        if (fwd_msgs := fwd.forwarded_messages) and text_depth:
            fwd_str = await parse_forwarded_messages(
                api, fwd_msgs, text_depth=text_depth - 1
            )
            attachments.append(
                f"С пересланными сообщениями:<blockquote expandable>{fwd_str.replace(SEP, "\n | ")}</blockquote>"
            )
            # attachments.extend(["С пересланными сообщениями:"] + fwd_str.split(SEP))

        elif fwd_msgs:
            attachments.append("С пересланными сообщениями...")

        attachments_str = SEP.join(attachments)
        user = await get_user_name(api, fwd.from_id)

        fwd_list.append(f"{user}: {fwd.text}\n{attachments_str}")

    fwd_string = SEP.join([("\n" + fwd_).replace("\n", SEP) for fwd_ in fwd_list])
    return fwd_string


async def parse_replied_message(
    api: VkApiMethod, reply_to_message: ReplyMessage, text_depth: bool | int = False
) -> str:
    reply_message_normal = Message(
        **(await api.messages.getById(message_ids=reply_to_message.id))["items"][0]
    )
    rtm = (
        await parse_message(
            reply_message_normal,
            api,
            text_depth=(0 if text_depth >= 0 else text_depth - 1),
        )
    )[0]
    rtm_str = ("\n" + rtm).replace("\n", SEP)
    return rtm_str


async def check_attached_messages(
    message: Message, to_add: list[str], api: VkApiMethod, text_depth: int
) -> None:
    if text_depth == 0:
        return

    if reply_to_message := message.reply_message:
        rtm_str = await parse_replied_message(
            api,
            reply_to_message,
            text_depth=(1 if text_depth >= 0 else text_depth - 1),
        )
        rtm_string = (
            f"С ответом на сообщение:<blockquote expandable>{rtm_str}</blockquote>"
        )
        to_add.append(rtm_string)

    if forwarded_messages := message.forwarded_messages:
        fwd_string = await parse_forwarded_messages(
            api, forwarded_messages, text_depth=text_depth - 1
        )
        forwarded_string = f"С пересланными сообщениями: <blockquote expandable>{fwd_string}</blockquote>"
        to_add.append(forwarded_string)


async def parse_message(
    message: Message,
    api: VkApiMethod,
    # text_depth=3,
    text_depth=-1,
) -> tuple[str, bool]:
    """Return output and chat_is_in_blocklist"""
    msg = (await api.messages.getById(message_ids=message.id))["items"][0]
    message = Message(**msg)
    text, conversation = await get_text_message(message, api, text_depth)
    is_in_blocklist = conversation in CHATS_BLACKLIST
    return text, is_in_blocklist


async def parse_event(
    event: Event,
    api: VkApiMethod,
    # text_depth=3,
    text_depth=-1,
) -> tuple[str, bool]:
    """Return output and chat_is_in_blocklist"""
    msg = (await api.messages.getById(message_ids=event.message_id))["items"][0]
    message = Message(**msg)
    text, conversation = await get_text_message(message, api, text_depth)
    is_in_blocklist = conversation in CHATS_BLACKLIST
    return text, is_in_blocklist


"""
type PHOTO_TYPES = str | bytes | pathlib.Path | io.BytesIO
PHOTO_MAX_LEN = 1

@overload
async def upload_photos(api: VkApiMethod, peer_id: int, photos: list[PHOTO_TYPES]) -> list[Photo]: ...
@overload
async def upload_photos(api: VkApiMethod, peer_id: int, photos: PHOTO_TYPES) -> Photo: ...
async def upload_photos(
    api: VkApiMethod, peer_id: int, photos: PHOTO_TYPES | list[PHOTO_TYPES]
) -> Photo | list[Photo]:
    # TODO: use single upload server
    photos = photos if isinstance(photos, list) else [photos]

    if len(photos) > PHOTO_MAX_LEN:
        # len(photo) = 13, 13 // 5 = 2
        result: list[Photo] = []
        for i in range(0, len(photos) // PHOTO_MAX_LEN):
            tmp = photos[PHOTO_MAX_LEN * i : PHOTO_MAX_LEN * (i + 1)]
            tmp_res = await upload_photos(api, peer_id, tmp)
            result.extend(tmp_res)
        return result

    files: list[io.BytesIO] = []
    for photo in photos:
        if isinstance(photo, str):
            raw = pathlib.Path(photo).read_bytes()
        elif isinstance(photo, bytes):
            raw = photo
        elif isinstance(photo, pathlib.Path):
            raw = photo.read_bytes()
        elif isinstance(photo, io.BytesIO):
            raw = bytes(photo.getbuffer())
        else:
            raise TypeError(f"Unknown type {type(photo)}!")
        fake_file = io.BytesIO(raw)
        files.append(fake_file)

    to_upload = dict(photo=files[0])
    # to_upload: dict[str, io.BytesIO] = {
    #     f"file{x}": y for (x, y) in zip(range(PHOTO_MAX_LEN), files)
    # }

    upload_server_info = GetMessagesUploadServer(**(await api.photos.getMessagesUploadServer(peer_id=peer_id)))

    upload_answer = UploadServerAnswer(
        **(
            await api._vk.http.post(
                upload_server_info.upload_url, files=to_upload
            )
        ).json()
    )

    result = await api.photos.saveMessagesPhoto(
        photo=upload_answer.photos_list,
        server=
    )
    # upload_answer.


    return Photo(**{})
"""
