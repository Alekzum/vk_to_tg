from importlib import import_module
from aiogram import Dispatcher
from aiogram_dialog import setup_dialogs
import pathlib


def include_routers(dp: Dispatcher, root_str="handlers"):
    setup_dialogs(dp)
    
    root = pathlib.Path(root_str)
    root_str = root.as_posix().replace("/", ".")
    files = root.glob("*.py")
    for file in files:
        module = import_module(".".join((root_str, file.with_suffix("").name)))
        dp.include_router(module.rt)
