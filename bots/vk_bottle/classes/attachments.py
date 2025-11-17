from pydantic import BaseModel
from typing import Any, List, Optional
import datetime


class Image(BaseModel):
    url: str
    width: int
    height: int


class Sticker(BaseModel):
    inner_type: str
    sticker_id: int
    product_id: int
    is_allowed: bool
    images: List[Image]
    images_with_background: List[Image]


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
    date: datetime.datetime
    id: int
    owner_id: int
    sizes: List[Size]
    text: str
    user_id: int
    web_view_token: Optional[str] = None
    has_tags: bool
    orig_photo: Optional[OrigPhoto] = None


class PhotoById(BaseModel):
    id: int
    album_id: int
    owner_id: int
    user_id: int
    text: str
    date: datetime.datetime
    has_tags: bool
    thumb_hash: str
    sizes: List[Size]
    width: Optional[int] = None
    height: Optional[int] = None


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
    media: Optional[Sticker | AudioMessage | Link | Photo | Any] = None

    def __init__(self, **kwargs):
        super().__init__(type=kwargs["type"], raw=kwargs, media=kwargs[kwargs["type"]])