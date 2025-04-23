from . import vk_messages
from . import user_settings


async def get_users() -> list[user_settings.UserInfo]:
    return await user_settings.get_users()


async def init_db():
    await vk_messages.init_db()
    await user_settings.init_db()
