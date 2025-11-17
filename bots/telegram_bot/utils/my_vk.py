from utils.config import Config
from utils.my_vk_api import AsyncVkApi, VkApiMethod
import httpx, json
from io import BytesIO
# from vk_api import vk_api  # type: ignore


async def get_vk_api(user_id: int) -> VkApiMethod:
    vk_client = AsyncVkApi(token=(await Config(user_id).load_values())._ACCESS_TOKEN)
    api = vk_client.get_api()
    return api


async def upload_photo(tg_user_id: int, photo: str | BytesIO) -> str:
    """Upload photo to VK and return photo's ID in format photo_{owner_id}_{photo_id}

    Args:
        user_id (int): photo's owner
        path (str): path to the photo

    Returns:
        str: photo's ID in the VK
    """    
    vk_api = await get_vk_api(user_id=tg_user_id)
    server = await vk_api.photos.getMessagesUploadServer()
    url = server["upload_url"].replace("\\", "")
    uploaded_photo_info = (await httpx.AsyncClient().post(url, files=dict(photo=photo))).json()
    
    photos = await vk_api.photos.saveMessagesPhoto(**uploaded_photo_info)
    photo_ = photos[0] if photos else None
    if photo_ is None:
        raise RuntimeError
    result = "photo{}_{}".format(photo_["owner_id"], photo_["id"])
    return result