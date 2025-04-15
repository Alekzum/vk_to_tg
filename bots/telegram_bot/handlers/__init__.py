from .common import rt as common_rt
from aiogram import Router
import logging


logger = logging.getLogger(__name__)
rt = Router(name=__name__)

# rt.include_routers(common_rt)