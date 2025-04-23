from aiogram import Router
import logging


logger = logging.getLogger(__name__)


def get_rt():
    from .handler_dev import rt as dev_rt
    from .handler_common import rt as common_rt
    from .handler_echo import rt as echo_rt
    from .handler_vk import rt as vk_rt
    rt = Router(name=__name__)

    rt.include_routers(
        dev_rt,
        vk_rt,
        common_rt,
        echo_rt,
    )

    return rt