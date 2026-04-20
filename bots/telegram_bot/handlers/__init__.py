from aiogram import Router
from utils.my_logging import getLogger


logger = getLogger(__name__)

rt = Router(name=__name__)
included_routers = set()

def get_rt():
    from .handler_dev import rt as dev_rt
    from .handler_common import rt as common_rt
    from .handler_echo import rt as echo_rt
    from .handler_vk import rt as vk_rt
    from .handler_vk_send import rt as vk_send_rt
    from .handler_settings import rt as settings_rt
    

    routers = (
        dev_rt,
        vk_rt,
        vk_send_rt,
        common_rt,
        echo_rt,
        settings_rt,
    )
    for r in routers:
        if r in included_routers:
            continue
        rt.include_router(r)
        included_routers.add(r)
            

    return rt
