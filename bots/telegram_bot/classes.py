from functools import partial

from utils.config import Config, OWNER_ID
from utils.my_logging import getLogger
from os import environ as ENVIRON
from typing import overload, Any
from pyrogram.client import Client
from pyrogram import raw, types, enums
from dataclasses import dataclass
import re


logger = getLogger(__name__)


URL_RE = re.compile(
    r"(https?:\/\/(www\.)?"
    r"[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,4}\b"
    r"([-a-zA-Z0-9@:%_\+.~#?&//=]*))"
)


# @cached(cache={})
@dataclass
class MyTelegram:
    config: Config
    chat_id: int
    tg: Client
    pinned_message_id: int = -1

    def __init__(
        self, chat_id: int = OWNER_ID, name="PyrogramVkontakteToTelegramBot"
    ):
        self.config = cfg = Config(chat_id)

        self.chat_id = chat_id
        class_tg: Client | None = getattr(MyTelegram, "tg", None)
        self.tg = class_tg or Client(
            name=name,
            api_id=ENVIRON["API_ID"],
            api_hash=ENVIRON["API_HASH"],
            bot_token=cfg._BOT_TOKEN,
            workdir="data",
            parse_mode=enums.ParseMode.HTML,
        )

        setattr(MyTelegram, "tg", self.tg)

    async def init(self) -> None:
        tg = self.tg
        if not tg.is_connected:
            is_authorized = await tg.connect()
            try:
                if not is_authorized:
                    await tg.authorize()
                await tg.invoke(raw.functions.updates.get_state.GetState())
            except (Exception, KeyboardInterrupt):
                await tg.disconnect()
                raise
            else:
                tg.me = await tg.get_me()
                await tg.initialize()

        await self.config.load_values()
        self.pinned_message_id = self.config.pinned_message_id

    @overload
    async def get_messages(self, message_ids: int) -> types.Message: ...
    @overload
    async def get_messages(
        self, message_ids: list[int]
    ) -> list[types.Message]: ...
    async def get_messages(
        self, message_ids: int | list[int]
    ) -> types.Message | list[types.Message]:
        msg = await self.tg.get_messages(
            chat_id=self.chat_id,
            message_ids=message_ids,
        )
        if msg is None:
            raise KeyError("Didn't found message with given ID :(")

        if isinstance(message_ids, list):
            msg = [msg] if not isinstance(msg, list) else msg
            return msg

        msg = msg[0] if isinstance(msg, list) else msg
        return msg

    async def send_text(
        self,
        text: str,
        reply_markup: types.InlineKeyboardMarkup
        | types.ReplyKeyboardMarkup
        | types.ReplyKeyboardRemove
        | types.ForceReply
        | None = None,
        reply_parameters: types.ReplyParameters | Any = None,
        link_preview_index: int = 0,
    ) -> types.Message:
        parsed = await self.tg.parser.parse(text, mode=self.tg.parse_mode)
        message = len(parsed["message"] or [])
        entities = len(parsed["entities"] or [])
        m = 4000
        if message > m or entities > 50:
            chunks = (
                text[x * m : ((x + 1) * m)] for x in range(len(text) // m)
            )
            msg = None
            for chunk in chunks:
                msg = await self.send_text(
                    chunk,
                    reply_markup=reply_markup,
                    reply_parameters=reply_parameters,
                    link_preview_index=link_preview_index,
                )
            if msg is None:
                raise Exception("???")
            return msg

        func = partial(
            self.tg.send_message,
            chat_id=self.chat_id,
            text=text,
            reply_parameters=reply_parameters,
            link_preview_options=types.LinkPreviewOptions(
                url=find_url(text, index=link_preview_index)
            ),
        )
        if reply_markup:
            return await func(
                reply_markup=reply_markup,
            )
        return await func()

    async def reply_text(
        self,
        msg_id: int,
        text: str,
        reply_markup: Any = None,
        link_preview_index: int = 0,
    ) -> types.Message:
        return await self.send_text(
            text=text,
            reply_markup=reply_markup,
            reply_parameters=types.ReplyParameters(message_id=msg_id),
            link_preview_index=link_preview_index,
        )

    async def edit_text(
        self,
        msg_id: int,
        text: str,
        reply_markup: Any = None,
        link_preview_index: int = 0,
    ) -> types.Message:
        msg = await self.tg.edit_message_text(
            chat_id=self.chat_id,
            message_id=msg_id,
            text=text,
            reply_markup=reply_markup,
            link_preview_options=types.LinkPreviewOptions(
                url=find_url(text, index=link_preview_index)
            ),
        )
        if isinstance(msg, bool):
            logger.error("Invalid message type", msg_type=type(msg))
            raise TypeError(f"{type(msg)=}!")
        return msg

    async def edit_reply_markup(
        self,
        msg_id: int,
        reply_markup: Any = None,
    ) -> types.Message:
        msg = await self.tg.edit_message_reply_markup(
            chat_id=self.chat_id,
            message_id=msg_id,
            reply_markup=reply_markup,
        )
        return msg

    async def edit_pinned_text(
        self, text: str, reply_markup: Any = None, link_preview_index: int = 0
    ):
        async def _edit_pinned_text(msg: types.Message):
            if msg.text == text:
                return

            return await self.edit_text(
                msg_id=msg.id,
                text=text,
                reply_markup=reply_markup,
                link_preview_index=link_preview_index,
            )

        if self.pinned_message_id != -1:
            msg = await self.tg.get_messages(
                chat_id=self.chat_id, message_ids=self.pinned_message_id
            )
            if msg is not None:
                return await _edit_pinned_text(msg)

        logger.debug(
            "Didn't got pinned message",
            chat_id=self.chat_id,
            pinned_message_id=self.pinned_message_id,
        )
        msg = await self.send_text(
            text=text,
            reply_markup=reply_markup,
            link_preview_index=link_preview_index,
        )
        await msg.pin(both_sides=True, disable_notification=True)
        self.config.pinned_message_id = self.pinned_message_id = msg.id
        await self.config.save_variables()
        logger.debug(
            "saved config for pinned_message_id", pinned_message_id=msg.id
        )
        return msg

    async def stop(self):
        await self.send_text("Бот остановлен.")
        if self.tg.is_connected:
            await self.tg.disconnect()


def find_url(text: str, index: int = 0) -> str:
    matches = URL_RE.findall(text)
    match = matches[index][0] if matches and len(matches) >= index - 1 else ""
    return match
