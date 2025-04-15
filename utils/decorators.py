from functools import wraps
import logging
import time


logger = logging.getLogger(__name__)
MAX_RETRY_COUNT = 3


def repeat_until_complete(func):
    @wraps(func)
    def inner(*args, _retries=0, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            if _retries >= MAX_RETRY_COUNT:
                raise
            logger.warning(f"{ex!r} #{_retries+1}/{MAX_RETRY_COUNT}")
            time.sleep(1)
            return inner(*args, **kwargs, _retries=_retries + 1)

    return inner


x = 0


def test_repeat():
    test_lambda = lambda: (
        globals().update({"x": print('increment "x"') or globals()["x"] + 1})
        or (globals()["x"] <= 1 and exec("raise Exception('LMAO')"))
        or 1
    )

    # Для сравнения - лямбда-функция в обычном виде
    # def test_function():
    #     global x

    #     print('increment "x"')
    #     x += 1
    #     if x <= 1:
    #         raise Exception("LMAO")
    #     return 1

    test = repeat_until_complete(test_lambda)
    result = test()
    print(f"{result=}")


if __name__ == "__main__":
    import pathlib
    exec(pathlib.Path().absolute().joinpath("utils", "my_logging.py").read_text())
    test_repeat()
