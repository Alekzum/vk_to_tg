from pydantic import BaseModel, Field
from enum import Enum
from typing import Any, Protocol, Literal, cast, List, Optional
import datetime

# for test
import pathlib
import json


class Sticker(BaseModel):
    inner_type: str
    sticker_id: int
    product_id: int
    is_allowed: bool


class AudioMessage(BaseModel):
    duration: int
    id: int
    link_mp3: str
    link_ogg: str
    owner_id: int
    access_key: str
    transcript: str
    transcript_state: str
    waveform: List[int]


class Size(BaseModel):
    height: int
    type: str
    width: int
    url: str


class OrigPhoto(BaseModel):
    height: int
    type: str
    url: str
    width: int


class Photo(BaseModel):
    album_id: int
    date: int
    id: int
    owner_id: int
    sizes: List[Size]
    text: str
    user_id: int
    web_view_token: str
    has_tags: bool
    orig_photo: OrigPhoto


class Link(BaseModel):
    url: str
    title: str
    caption: str
    photo: Photo
    target: str
    is_favorite: bool


class Attachment(BaseModel):
    type: str
    raw: dict
    media: Optional[Sticker | AudioMessage | Link | Any] = None

    def __init__(self, **kwargs):
        super().__init__(type=kwargs["type"], raw=kwargs, media=kwargs[kwargs["type"]])
        # self.type = kwargs["type"]
        # self.media = kwargs[self.type]
        # self.raw = kwargs

    # @property
    # def media(self) -> Sticker | AudioMessage | Link | Any:
    #     return getattr(self, self.type, self.media_)


class Reaction(BaseModel):
    reaction_id: int
    count: int
    user_ids: List[int]


class MessageActionType(Enum):
    CHAT_PHOTO_UPDATE = "chat_photo_update"
    CHAT_PHOTO_REMOVE = "chat_photo_remove"
    CHAT_CREATE = "chat_create"
    CHAT_TITLE_UPDATE = "chat_title_update"
    CHAT_INVITE_USER = "chat_invite_user"
    CHAT_KICK_USER = "chat_kick_user"
    CHAT_PIN_MESSAGE = "chat_pin_message"
    CHAT_UNPIN_MESSAGE = "chat_unpin_message"
    CHAT_INVITE_USER_BY_LINK = "chat_invite_user_by_link"


class MemberIdValid(Protocol):
    type: Literal[
        MessageActionType.CHAT_INVITE_USER,
        MessageActionType.CHAT_KICK_USER,
        MessageActionType.CHAT_PIN_MESSAGE,
        MessageActionType.CHAT_UNPIN_MESSAGE,
    ]
    member_id: int


class MemberIdInvalid(Protocol):
    type: Literal[
        MessageActionType.CHAT_PHOTO_UPDATE,
        MessageActionType.CHAT_PHOTO_REMOVE,
        MessageActionType.CHAT_CREATE,
        MessageActionType.CHAT_TITLE_UPDATE,
        MessageActionType.CHAT_INVITE_USER_BY_LINK,
    ]
    member_id: None


class MessageAction(BaseModel):
    type: MessageActionType
    message: Optional[str]
    conversation_message_id_: Optional[int] = Field(
        None, alias="conversation_message_id"
    )
    member_id_: Optional[int] = Field(None, alias="member_id")

    @property
    def member_id(self) -> int | None:
        """Just get correct member id. Types CHAT_INVITE_USER, CHAT_KICK_USER, CHAT_PIN_MESSAGE, CHAT_UNPIN_MESSAGE will return integer

        Returns:
            (int | None): just member id if type is correct
        """

        if self._valid_for_member_id:
            member_id = cast(int, self.member_id_)
            return member_id
        return None

    @property
    def _valid_for_member_id(self):
        return self.type in {
            MessageActionType.CHAT_INVITE_USER,
            MessageActionType.CHAT_KICK_USER,
            MessageActionType.CHAT_PIN_MESSAGE,
            MessageActionType.CHAT_UNPIN_MESSAGE,
        }


class ForwardMessage(BaseModel):
    # model_type: Literal["m1"]
    attachments: List[Attachment]
    text: str
    conversation_message_id: int
    from_id: int
    # random_id: int = 0
    # peer_id: int


class ReplyMessage(BaseModel):
    date: datetime.datetime
    from_id: int
    text: str
    attachments: List[Attachment]
    conversation_message_id: int
    id: int
    peer_id: int


class Message(BaseModel):
    date: datetime.datetime
    from_id: int
    id: int
    version: int
    out: int
    important: bool
    is_hidden: bool
    attachments: List[Attachment]
    conversation_message_id: int
    text: str
    peer_id: int
    random_id: int
    forwarded_messages: List[ForwardMessage] = Field(alias="fwd_messages")
    action: Optional[MessageAction] = None
    reply_message: Optional["ReplyMessage"] = None
    reactions: Optional[List[Reaction]] = None
    last_reaction_id: Optional[int] = None
    update_time: Optional[int] = None

    def __post_init__(self):
        self.date = self.date + datetime.timedelta(hours=4)

    # @property
    # def from_friend(self) -> bool:
    #     return bool((self.flags or 0) & MessageFlags.FRIENDS)

    # @property
    # def is_spam(self) -> bool:
    #     return bool((self.flags or 0) & MessageFlags.SPAM)

    # @property
    # def is_deleted(self) -> bool:
    #     return bool((self.flags or 0) & MessageFlags.DELETED)

    # @property
    # def is_deleted_for_all(self) -> bool:
    #     return bool((self.flags or 0) & MessageFlags.DELETED)


def test():
    msgs_path = pathlib.Path(__file__).absolute().parent.parent.parent.joinpath("tests", "messages.json")
    msgs = json.loads(msgs_path.read_text("utf-8"))
    messages = [Message(**msg) for msg in msgs]
    # print(messages)


if __name__ == "__main__":
    test()
