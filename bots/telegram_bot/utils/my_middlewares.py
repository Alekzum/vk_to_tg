from typing import Callable, Dict, Any, Awaitable, TypedDict, override
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, User, Chat
import time


class Translation(TypedDict):
    seconds_to_str: dict[int | str, str]
    """Dict for converting seconds to string"""
    error_too_fast: str
    """Message which need to be used with `.format(remain_time=..., unit_string=...)`"""


translations: dict[str, Translation] = dict(
    ru=Translation(
        seconds_to_str={
            1: "секунду",
            2: "секунды",
            3: "секунды",
            4: "секунды",
            "default": "секунд",
        },
        error_too_fast="слишком быстро, подожди чут-чут 🤏, вот прям {remain_time:.1f} {unit_string}",
    ),
    en=Translation(
        seconds_to_str={1: "second", "default": "seconds"},
        error_too_fast="Too fast, wait just {remain_time:.1f} {unit_string}",
    ),
)
"""Get translation_table by language code.

In that table there is two fields: seconds_to_str and error_too_fast.

Usage:

```python
unit_string = seconds_to_str.get(last_digit, seconds_to_str['default'])
too_fast_message = error_too_fast.format(remain_time=remain_time, unit_string=unit_string)
```
"""


class CooldownMiddleware(BaseMiddleware):
    """If from previous update from user didn't pass *cooldown* seconds, then update will not invoked"""

    def __init__(self, cooldown: float = 0.5):
        self.cooldown = cooldown
        self.times: dict[int, float] = dict()

    @override
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        from_user: User | None = getattr(event, "from_user", None)
        sender_chat: Chat | None = getattr(event, "from_user", None)
        if from_user is not None:
            uid = from_user.id
            language_code = from_user.language_code or "en"

        elif sender_chat is not None:
            uid = sender_chat.id
            language_code = "en"

        else:
            raise RuntimeError("Unknown sender for event!", event)
            # return await handler(event, data)

        translation_table = translations.get(language_code, translations["en"])

        cur_time = time.time()
        delta_time = cur_time - self.times.get(uid, 0)

        is_too_fast = delta_time < self.cooldown

        if isinstance(event, CallbackQuery) and is_too_fast:
            too_fast_message_raw = translation_table["error_too_fast"]
            unit_string = translation_table["seconds_to_str"]

            remain_time = self.cooldown - delta_time
            remains_int: int = int(remain_time)
            remains_last_d = remains_int % 10

            too_fast_message = too_fast_message_raw.format(
                remain_time=remain_time,
                unit_string=unit_string.get(remains_last_d, unit_string["default"]),
            )
            await event.answer(too_fast_message)
            return

        elif is_too_fast:
            return

        self.times[uid] = cur_time
        return await handler(event, data)
