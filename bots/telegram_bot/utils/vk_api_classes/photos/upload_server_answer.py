from pydantic import BaseModel
from typing import List, Optional


class UploadServerAnswer(BaseModel):
    server: int
    photos_list: str
    aid: int
    hash: str
