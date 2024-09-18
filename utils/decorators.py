from functools import wraps
import logging
import time


logger = logging.getLogger(__name__)
MAX_RETRY_COUNT = 10


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
            return inner(*args, **kwargs, _retries=_retries+1)
    return inner
