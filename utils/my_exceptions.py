import traceback
import json

from typing import Callable, Any


def handle_exception(ex: Exception):
    format_dict = lambda d: (
        {k: format_dict(v) for (k, v) in d.items() if str(k)[0] != "_"}  # type: ignore
        if isinstance(d, dict)
        else d
    )
    trace = ex.__traceback__
    indent = None
    kwargs: dict[str, Any] = dict(
        sort_keys=True, default=str, ensure_ascii=False, indent=indent
    )
    for tb, line in traceback.walk_tb(trace):
        globals_ = format_dict(tb.f_globals)
        globals_ = json.dumps(globals_, **kwargs)

        locals_ = format_dict(dict(tb.f_locals))
        locals_ = json.dumps(locals_, **kwargs)

        # print(f"{type(tb.f_globals)=}, {type(tb.f_locals)=}")
        # print(f"{type(globals_)=}, {type(locals_)=}")
        print(
            f"""at {tb.f_code.co_filename}, line {line} namespace is:
- globals: {globals_}

- locals: {locals_}

"""
        )
    raise
