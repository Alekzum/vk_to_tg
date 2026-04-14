from . import vk_interface
from . import user_settings


async def get_users() -> list[user_settings.UserInfo]:
    return await user_settings.UserSettingsManager.UserManager.get_all()


async def init_db():
    await vk_interface.init_db()
    await user_settings.init_db()
