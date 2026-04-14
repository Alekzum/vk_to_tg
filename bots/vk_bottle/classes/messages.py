from pydantic import BaseModel, Field
from typing import cast, List, Optional
import datetime

from .attachments import Attachment
from .enums import MessageActionType


class Reaction(BaseModel):
    reaction_id: int
    count: int
    user_ids: List[int]


class MessageActionPhoto(BaseModel):
    photo_50: str
    photo_100: str
    photo_200: str


class MessageAction(BaseModel):
    type: MessageActionType
    message: Optional[str] = None
    conversation_message_id_: Optional[int] = Field(
        None, alias="conversation_message_id"
    )
    member_id_: Optional[int] = Field(None, alias="member_id")
    text_: Optional[str] = Field(None, alias="text")
    email_: Optional[str] = Field(None, alias="email")
    photo_: Optional[dict] = Field(None, alias="photo")

    @property
    def photo(self) -> None | MessageActionPhoto:
        if self.photo_ is None or not self.photo_:
            return None
        return MessageActionPhoto(**self.photo_)

    @property
    def email(self):
        # member_id = self.member_id
        if self.type == MessageActionType.CHAT_KICK_USER:
            assert isinstance(self.member_id, int), "wtf"
            if self.member_id >= 0:
                return None
        if self.type != MessageActionType.CHAT_INVITE_USER:
            return None
        email = cast(str, self.email_)
        return email

    @property
    def text(self):
        if self.type not in {
            MessageActionType.CHAT_CREATE,
            MessageActionType.CHAT_TITLE_UPDATE,
        }:
            return None
        text = cast(str, self.text_)
        return text

    @property
    def member_id(self) -> int | None:
        if self.type not in {
            MessageActionType.CHAT_INVITE_USER,
            MessageActionType.CHAT_KICK_USER,
            MessageActionType.CHAT_PIN_MESSAGE,
            MessageActionType.CHAT_UNPIN_MESSAGE,
        }:
            return None
        member_id = cast(int, self.member_id_)
        return member_id


class BaseMessage(BaseModel):
    attachments: List[Attachment]
    text: str
    conversation_message_id: int
    from_id: int
    forwarded_messages: List["ForwardMessage"] = Field(
        alias="fwd_messages", default_factory=lambda: list()
    )
    reply_message: Optional["ReplyMessage"] = None


class ForwardMessage(BaseMessage):
    pass
    # attachments: List[Attachment]
    # text: str
    # conversation_message_id: int
    # from_id: int
    # fwd_messages: "List[ForwardMessage]" = Field(default_factory=lambda: list())
    # reply_message: "Optional[ReplyMessage]" = None


class ReplyMessage(ForwardMessage):
    # pass
    inner_date: datetime.datetime = Field(..., alias="date")
    from_id: int
    id: int
    peer_id: int

    @property
    def date(self):
        return self.inner_date + datetime.timedelta(hours=4)

    @property
    def link(self):
        return f"https://web.vk.me/convo/{self.peer_id}?cmdif={self.conversation_message_id}"


class Action(BaseModel):
    label: str
    type: str
    payload: str


class Button(BaseModel):
    action: Action
    color: str


class Keyboard(BaseModel):
    one_time: bool
    buttons: List[List[Button]]
    author_id: int
    inline: bool


class Message(ReplyMessage):
    # date: datetime.datetime
    # from_id: int
    # id: int
    # peer_id: int
    version: int
    out: int
    important: bool
    is_hidden: bool
    random_id: Optional[int] = None
    action: Optional[MessageAction] = None
    reactions: Optional[List[Reaction]] = None
    last_reaction_id: Optional[int] = None
    update_time: Optional[int] = None
    keyboard: Optional[Keyboard] = None
