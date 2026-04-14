from pydantic import BaseModel


class GetUploadServer(BaseModel):
    album_id: int
    upload_url: str
    user_id: int
