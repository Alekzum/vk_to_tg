from typing import Any
import traceback
from utils.my_logging import getLogger
import asyncio
import json
import sys


IGNORE_FILES = {
    "aiogram",
    "asyncio",
}

logger = getLogger(__name__)


def asyncio_exception_handler(loop, context):
    # log exception
    logger.error(f"{context['exception']}!")


# callback func called for all tasks
def helper_done_callback(task):
    try:
        # get any exception raised
        ex = task.exception()
        # check task for exception
        if ex:
            # report the exception
            ex_str = traceback.format_exc()
            logger.error(f"{ex}! {ex_str}")
    except asyncio.exceptions.CancelledError:
        pass


# helper for creating all tasks
def create_task_helper(coroutine, **kwargs):
    # wrap and schedule the task
    task = asyncio.create_task(coroutine, **kwargs)
    # add custom callback to task
    task.add_done_callback(helper_done_callback)
    # return the task that was created
    return task


def handle_exception(ex: Exception):
    def format_key(k):
        return (
            str(k) if not (k is None or isinstance(k, (str, int, float, bool))) else k
        )

    def limit_string(obj):
        return str(obj) if len(str(obj)) < 1000 else str(obj)[:999] + "…"

    def format_dict(d):
        return (
            {format_key(k): format_dict(v) for (k, v) in d.items() if str(k)[0] != "_"}
            if isinstance(d, dict)
            else limit_string(d)
        )

    trace = ex.__traceback__
    indent = 4
    kwargs: dict[str, Any] = dict(default=str, ensure_ascii=False, indent=indent)
    for tb, line in traceback.walk_tb(trace):
        if (
            any(i in tb.f_code.co_filename for i in IGNORE_FILES)
            and "--loud" not in sys.argv[1:]
        ):
            info = "SKIPPED"
        else:
            globals_ = format_dict(tb.f_globals)
            globals_ = json.dumps(globals_, **kwargs)

            locals_ = format_dict(dict(tb.f_locals))
            locals_ = json.dumps(locals_, **kwargs)

            info = f"\n- globals: {globals_}\n\n- locals: {locals_}\n\n"
        # elif tb.f_code.co_filename in IGNORE_FILES:
        # info = "IGNORED"

        # print(f"{type(tb.f_globals)=}, {type(tb.f_locals)=}")
        # print(f"{type(globals_)=}, {type(locals_)=}")
        print(f"""at {tb.f_code.co_filename}, line {line} namespace is: {info}""")
