from pydantic import BaseModel
from typing import Optional


class GetMessagesUploadServer(BaseModel):
    album_id: int
    upload_url: str
    user_id: int
    group_id: Optional[int] = None