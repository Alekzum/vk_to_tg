from pydantic import BaseModel


class UploadServerAnswer(BaseModel):
    server: int
    photos_list: str
    aid: int
    hash: str
