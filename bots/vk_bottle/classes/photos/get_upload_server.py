from pydantic import BaseModel
from typing import List, Optional


class GetUploadServer(BaseModel):
    album_id: int
    upload_url: str
    user_id: int
    