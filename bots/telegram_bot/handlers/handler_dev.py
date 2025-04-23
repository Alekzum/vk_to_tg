from utils.config import OWNER_ID
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command, CommandObject
from aiogram.utils import formatting
from aiogram_dialog import DialogManager
from aiogram_dialog.api.exceptions import NoContextError
from typing import Any
import logging

# from utils.text2image import text_to_image
import json
import html


logger = logging.getLogger(__name__)
rt = Router()

COMMANDS_DESCRIPTION: dict[str, str] = dict(
    dev="Получить этот лист с командами",
    reload="Перезапустить текущее окно",
    cancel="Отменить текущий диалог",
    get_key="Получить объект из какого-либо словаря менеджера диалога",
    del_key="Удалить объект из какого-либо словаря менеджера диалога",
    global_data="Получить доступные глобальные переменные в функции",
    local_data="Получить доступные переменные в функции",
    dialog_data="Получить доступные переменные в диалоге",
    middleware_data="Получить доступные переменные в функции",
    current_data="Получить доступные переменные в функции и диалоге",
    current_state="Получить текущее состояние бота",
)

HELP_TEXT = formatting.as_marked_section(
    'Доступные команды "разработчика"',
    *[formatting.as_key_value(f"/{k}", v) for (k, v) in COMMANDS_DESCRIPTION.items()],
).as_html()


def clear_dict(d: dict | Any, _d=3) -> dict:
    return (
        {k: clear_dict(v, _d - 1) for (k, v) in d.copy().items() if k[0] != "_"}
        if isinstance(d, dict) and _d > 1
        else d
    )


@rt.message(F.from_user.id.in_({OWNER_ID}), Command("dev"))
async def about_commands(message: Message, dialog_manager: DialogManager):
    await message.answer(HELP_TEXT)


@rt.message(F.from_user.id.in_({OWNER_ID}), Command("cancel"))
async def cancel_state(_: Message, dialog_manager: DialogManager):
    await dialog_manager.reset_stack()


@rt.message(F.from_user.id.in_({OWNER_ID}), Command("get_key"))
@rt.message(F.from_user.id.in_({OWNER_ID}), Command("del_key"))
async def cmd_delete_data(
    message: Message, dialog_manager: DialogManager, command: CommandObject
):
    args = command.args
    if not args:
        return await message.answer("need path to object")
    path = args.split(" ")
    first_object = path[0]
    path_ = path[1:-1]
    last_object = path[-1]
    try:
        obj: dict = getattr(dialog_manager, first_object)
        for parent in path_:
            obj = obj[parent]
        # await message.answer(f"{obj=}")
    except (KeyError, AttributeError) as ex:
        return await message.answer(f"cannot find this path because {ex}")

    match command.command:
        case "del_key":
            deleted_object = obj.pop(last_object)
            await message.answer(html.escape(f"{deleted_object=}"))
            logger.debug(f"{deleted_object!r}, {deleted_object!s}")
        case "get_key":
            required_object = obj[last_object]
            await message.answer(
                html.escape(f"{required_object=}, {required_object=!r}")
            )


@rt.message(F.from_user.id.in_({OWNER_ID}), Command("middleware_data"))
@rt.message(F.from_user.id.in_({OWNER_ID}), Command("dialog_data"))
@rt.message(F.from_user.id.in_({OWNER_ID}), Command("global_data"))
@rt.message(F.from_user.id.in_({OWNER_ID}), Command("local_data"))
@rt.message(F.from_user.id.in_({OWNER_ID}), Command("current_data"))
async def cmd_data(
    message: Message, dialog_manager: DialogManager, command: CommandObject
):
    required_data = dict(
        middleware_data=dict(middleware_data=dialog_manager.middleware_data),
        dialog_data=dict(dialog_data=dialog_manager.dialog_data),
        global_data=globals().copy(),
        local_data=locals().copy(),
    )
    required_data["current_data"] = required_data.copy()
    required_data = clear_dict(required_data)

    data = required_data[command.command]
    try:
        raw = html.escape(
            json.dumps(data, indent=4, ensure_ascii=False, sort_keys=True, default=str)
        )
        msgs = [raw[4000 * i : 4000 * (i + 1)] for i in range(0, len(raw) // 2000)]
        [await message.answer(msg) for msg in msgs if msg.strip()]
        # path = await text_to_image(
        #     json.dumps(data, indent=4, ensure_ascii=False, sort_keys=True, default=str)
        # )
        # await message.answer("Current data")
        # await message.answer_document(
        #     BufferedInputFile(path.read_bytes(), "result.png"), caption="Current data"
        # )
    except NoContextError:
        await message.answer(f"You are not in dialog now")
    # except Exception as ex:
    #     await message.answer(f"Didn't fetch data because {ex=}")


@rt.message(F.from_user.id.in_({OWNER_ID}), Command("current_state"))
async def cmd_start(message: Message, dialog_manager: DialogManager):
    try:
        current_state = dialog_manager.current_context().state
        string = current_state.state
        await message.answer(f"Current state: {string}")
    except NoContextError:
        await message.answer(f"You are not in dialog now")
    except Exception as ex:
        await message.answer(f"Didn't fetch current window because {ex=}")
