from pydantic import BaseModel
from typing import Literal, List, Optional


class Peer(BaseModel):
    id: int
    type: Literal["chat", "group", "user"]
    local_id: int


class SortId(BaseModel):
    major_id: int
    minor_id: int


class CanWrite(BaseModel):
    allowed: bool


class PinnedMessage(BaseModel):
    conversation_message_id: int
    id: int
    date: int
    from_id: int
    peer_id: int
    text: str
    attachments: List


class Photo(BaseModel):
    photo_50: str
    photo_100: str
    photo_200: str
    is_default_photo: bool
    is_default_call_photo: bool


class Acl(BaseModel):
    can_change_info: bool
    can_change_invite_link: bool
    can_change_pin: bool
    can_invite: bool
    can_promote_users: bool
    can_see_invite_link: bool
    can_moderate: bool
    can_copy_chat: bool
    can_call: bool
    can_use_mass_mentions: bool
    can_change_style: bool
    can_send_reactions: bool


class ChatSettings(BaseModel):
    title: str
    state: str
    members_count: int
    owner_id: int
    pinned_messages_count: int
    photo: Optional[Photo] = None
    active_ids: List
    is_group_channel: bool
    acl: Acl
    is_service: bool
    pinned_message: Optional[PinnedMessage] = None
    admin_ids: Optional[List[int]] = None
    description: Optional[str] = None
    is_disappearing: Optional[bool] = None
    type_mask: Optional[int] = None


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


class CurrentKeyboard(BaseModel):
    one_time: bool
    buttons: List[List[Button]]
    author_id: int
    inline: bool


class Conversation(BaseModel):
    peer: Peer
    last_message_id: int
    last_conversation_message_id: int
    in_read: int
    out_read: int
    in_read_cmid: int
    out_read_cmid: int
    version: int
    is_marked_unread: bool
    important: bool
    can_write: CanWrite
    can_send_money: bool
    can_receive_money: bool
    peer_flags: int
    chat_settings: Optional[ChatSettings] = None
    style: Optional[str] = None
    sort_id: Optional[SortId] = None
    current_keyboard: Optional[CurrentKeyboard] = None
