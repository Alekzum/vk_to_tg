from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from typing import Literal, cast, Sequence


INPUT_DATA_NAME = [
    "url",
    "callback",
    "callback_data",
    "switch_inline_query",
    "switch_inline_query_current_chat"
]

INPUT_KEYS = (
    Literal[
        "url",
        "callback",
        "callback_data",
        "switch_inline_query",
        "switch_inline_query_current_chat"
    ]
    | str
)
type INPUT_FIELDS = dict[
    INPUT_KEYS,
    str,
]
type INPUT_FIELDS2 = tuple[
    INPUT_KEYS,
    str,
]
type INPUT_THING_FIELD = tuple[str, dict[INPUT_KEYS, str] | tuple[INPUT_KEYS, str]]
type VALID_FIELD = INPUT_FIELDS | INPUT_FIELDS2 | tuple[str, str] | dict[str, str]


def convert_(to_fill: INPUT_KEYS, text: str, fill_value: str) -> InlineKeyboardButton:
    match to_fill:
        case "url":
            return InlineKeyboardButton(text=text, url=fill_value)
        case "callback":
            return InlineKeyboardButton(text=text, callback_data=fill_value)
        case "callback_data":
            return InlineKeyboardButton(text=text, callback_data=fill_value)
        case "switch_inline_query":
            return InlineKeyboardButton(text=text, switch_inline_query=fill_value)
        case "switch_inline_query_current_chat":
            return InlineKeyboardButton(
                text=text, switch_inline_query_current_chat=fill_value
            )
        case _:
            raise KeyError(f"Except one of {INPUT_KEYS.__args__}, not {to_fill!r}!")


def make_button_url(text: str, url: str) -> InlineKeyboardMarkup:
    """Make a single button with text and callback data"""
    # return InlineKeyboardBuilder().button(text=text, url=url).as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]]
    )


def make_button(text: str, callback_data: str) -> InlineKeyboardMarkup:
    # return InlineKeyboardBuilder().button(text=text, callback_data=callback_data).as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    )


def make_row(*items: dict[str, str] | tuple[str, str]) -> InlineKeyboardMarkup:
    # builder = InlineKeyboardBuilder()
    # for item in items:
    #     text, data = item
    #     builder = builder.button(text=text, callback_data=data)
    # return builder.adjust(8).as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=text, callback_data=data)
                for item in items
                for (text, data) in [parse_field(item)]
            ]
        ]
    )


def make_column(*items: VALID_FIELD) -> InlineKeyboardMarkup:
    # builder = InlineKeyboardBuilder()
    # for item in items:
    #     text, data = item
    #     builder = builder.button(text=text, callback_data=data)
    # return builder.adjust(1).as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data)]
            for item in items
            for (text, data) in [parse_field(item)]
        ]
    )


def make_keyboard(*items: Sequence[VALID_FIELD]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=text, callback_data=data)
                for (text, data) in row
            ]
            for row in items
        ]
    )
    # builder = InlineKeyboardBuilder()
    # for row in items:
    #     temp = InlineKeyboardBuilder()
    #     for item in row:
    #         text, data = item
    #         temp.button(text=text, callback_data=data)
    #     builder.row(*list(temp.buttons))
    # return builder.as_markup()


def convert(text: str, data: VALID_FIELD) -> InlineKeyboardButton:
    data_ = parse_field(data)
    return convert_(data_[0], text, data_[1])


def check_data(data: str):
    if data not in INPUT_DATA_NAME:
        raise ValueError(f"Excepted one of {INPUT_DATA_NAME}, not {data}!")


def make_button_thing(text: str, data: VALID_FIELD) -> InlineKeyboardMarkup:
    """Valid thing fields:
    - url
    - callback
    - switch_inline_query
    - switch_inline_query_current_chat
    - switch_inline_query_chosen_chat
    """
    # return InlineKeyboardBuilder().button(text=text, **{x: y for (x, y) in getattr(data, "items", lambda: [data])()}).as_markup()
    return InlineKeyboardMarkup(inline_keyboard=[[convert(text, data)]])


def make_row_thing(*items: INPUT_THING_FIELD) -> InlineKeyboardMarkup:
    """Usage: `func(("text", ("field", "data")), ("text", ("field", "data")))`

    Valid thing fields:
    - url
    - callback
    - switch_inline_query
    - switch_inline_query_current_chat
    - switch_inline_query_chosen_chat
    """
    # builder = InlineKeyboardBuilder()
    # for item in items:
    #     text, data = item
    #     builder = builder.button(
    #         text=text, **{x: y for (x, y) in getattr(data, "items", lambda: [data])()}
    #     )
    # return builder.adjust(8).as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[[convert(text, pair) for (text, pair) in items]]
    )


def make_column_thing(*items: INPUT_THING_FIELD) -> InlineKeyboardMarkup:
    """Usage: `func(("text", ("field", "data")), ("text", ("field", "data")))`

    Valid thing fields:
    - url
    - callback_data
    - switch_inline_query
    - switch_inline_query_current_chat
    - switch_inline_query_chosen_chat
    """
    # builder = InlineKeyboardBuilder()
    # for item in items:
    #     text, data = item
    #     if data not in INPUT_DATA_NAME:
    #         raise ValueError(f"Excepted one of {INPUT_DATA_NAME}, not {data}!")
    #     builder = builder.button(text=text, **{x: y for (x, y) in getattr(data, "items", lambda: [data])()})
    # return builder.adjust(1).as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[[convert(text, pair)] for (text, pair) in items]
    )


def make_keyboard_thing(*items: Sequence[INPUT_THING_FIELD]) -> InlineKeyboardMarkup:
    """Usage: `func([("text", ("field", "data")), ("text", ("field", "data"))], [("text", ("field", "data"))])`

    Valid thing fields:
    - url
    - callback
    - switch_inline_query
    - switch_inline_query_current_chat
    - switch_inline_query_chosen_chat
    """
    # builder = InlineKeyboardBuilder()
    # for row in items:
    #     temp = InlineKeyboardBuilder()
    #     for item in row:
    #         text, data = item
    #         temp.button(text=text, **{x: y for (x, y) in getattr(data, "items", lambda: [data])()})
    #     builder.row(*list(temp.buttons))
    # return builder.as_markup()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [convert(text, pair) for (text, pair) in pairs] for pairs in items
        ]
    )


def parse_field(item: VALID_FIELD) -> tuple[INPUT_KEYS, str]:
    if isinstance(item, tuple):
        return cast(tuple[INPUT_KEYS, str], item)
    elif isinstance(item, dict):
        return cast(tuple[INPUT_KEYS, str], list(item.items())[0])
    raise TypeError(f"Excepted tuple or dict, not {type(item)}")


EMPTY_BUTTON = make_button("Тут ничего нет", "Ты думал тут что-то будет?")
# MENU_BUTTON = make_button("Меню", "menu")
# """ text="Меню", callback_data="menu" """

# CANCEL_BUTTON = make_button("Отмена", "cancel")
# """ text="Отмена", callback_data="cancel" """

BUTTON_TEMPLATE = make_button("♿️♿️♿️", "unhandled_lol")

make_button("a", "a")
make_row(*[(i, i) for i in "abc"])
make_column(*[(i, i) for i in "abc"])
make_keyboard(*[[(i, i1) for i in "abc"] for i1 in "abc"])

make_button_thing("a", ("callback", "a"))
make_row_thing(*[(i, ("callback", i)) for i in "abc"])
make_column_thing(*[(i, ("callback", i)) for i in "abc"])
make_keyboard_thing(*[[(i, ("callback", i + i1)) for i in "abc"] for i1 in "abc"])
# """ text="♿️♿️♿️", callback_data="unhandled_lol" """
