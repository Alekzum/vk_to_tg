from logging import Logger
from structlog import wrap_logger, get_logger
from pathlib import Path
from importlib import import_module
import pip


def try_import(module):
    try:
        return import_module(module)
    except Exception:
        return None


def wrap_loggers():
    for pair in (
        ("aiogram",),
        ("pyrogram",),
        ("vkbottle.modules",),
        (
            "utils",
            Path(),
        ),
        # ("httpcore",),
        # ("urllib",),
        ("urllib3",),
        # ("asyncio",),
    ):
        try:
            wrap_loggers_module(pair[0], *pair[1:])
        except Exception:
            logger.warning(
                "Didn't wrapped module", module_name=pair[0], exc_info=True
            )


def wrap_loggers_module(
    module_name: str, relative_to: Path = Path(pip.__file__).parent.parent
):
    module = try_import(module_name)
    if module is None:
        logger.error(
            f"Didn't found module {module_name}",
            exc_info=True,
        )
        return

    path = Path(module.__file__ or "").parent

    modules = tuple(
        r
        for x in sorted(path.glob("**/[!_]*.py"))
        if x.is_file()
        and (
            r := try_import(
                x.relative_to(relative_to.absolute())
                .as_posix()
                .removesuffix(".py")
                .replace("/", ".")
            )
        )
        is not None
    )

    modules_loggers = tuple(
        (m, _loggers)
        for m in modules
        if (
            _loggers := tuple(
                n for n in dir(m) if isinstance(getattr(m, n, None), Logger)
            )
        )
    )
    for module, loggers in modules_loggers:
        for logger_ in loggers:
            raw_logger = getattr(module, logger_)
            setattr(module, logger_, wrap_logger(raw_logger))


logger = get_logger()


if __name__ == "__main__":
    wrap_loggers()
