from .conversations import Conversation
from .messages import Message
from pydantic import BaseModel
from typing import List, Optional


class GetConversationsItem(BaseModel):
    conversation: Conversation
    last_message: Message


class GetConversationsResponse(BaseModel):
    count: int
    items: List[GetConversationsItem]
    unread_count: Optional[int] = None


class GetConversations(BaseModel):
    response: GetConversationsResponse
