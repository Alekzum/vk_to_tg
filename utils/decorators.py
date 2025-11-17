from functools import wraps
from utils.my_logging import getLogger
import asyncio
import time


logger = getLogger(__name__)
MAX_RETRY_COUNT = 3


def repeat_until_complete(func):
    @wraps(func)
    def inner_sync(*args, _retries=0, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            if _retries >= MAX_RETRY_COUNT:
                raise
            logger.warning(f"{ex!r} #{_retries + 1}/{MAX_RETRY_COUNT}")
            time.sleep(1)
            return inner_sync(*args, **kwargs, _retries=_retries + 1)

    @wraps(func)
    async def inner_async(*args, _retries=0, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as ex:
            if _retries >= MAX_RETRY_COUNT:
                raise
            logger.warning(f"{ex!r} #{_retries + 1}/{MAX_RETRY_COUNT}")
            await asyncio.sleep(1)
            return await inner_async(*args, **kwargs, _retries=_retries + 1)

    return inner_async if asyncio.iscoroutinefunction(func) else inner_sync


x = 0


def test_repeat():
    def test_lambda():
        return (
            globals().update(
                {"x": logger.debug('increment "x"') or globals()["x"] + 1}
            )
            or (globals()["x"] <= 1 and exec("raise Exception('LMAO')"))
            or 1
        )

    # Для сравнения - лямбда-функция в обычном виде
    # def test_function():
    #     global x

    #     logger.debug('increment "x"')
    #     x += 1
    #     if x <= 1:
    #         raise Exception("LMAO")
    #     return 1

    test = repeat_until_complete(test_lambda)
    result = test()
    logger.debug(f"{result=}")


if __name__ == "__main__":
    import pathlib

    exec(
        pathlib.Path().absolute().joinpath("utils", "my_logging.py").read_text()
    )
    test_repeat()
