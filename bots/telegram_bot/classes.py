from utils.my_classes import TgMessage
from dataclasses import dataclass
from typing import Optional

from utils.decorators import repeat_until_complete

from utils.config import Config, OWNER_ID
from httpx import Client, AsyncClient
import logging


logger = logging.getLogger(__name__)


@dataclass
class ResponseParameters:
    migrate_to_ADMIN_IDS: Optional[int]
    """The group has been migrated to a supergroup with the specified identifier. This number may have more than 32 significant bits and 
    some programming languages may have difficulty/silent defects in interpreting it. But it has at most 52 significant bits, so a signed
    64-bit integer or double-precision float type are safe for storing this identifier."""
    retry_after: Optional[int]
    """In case of exceeding flood control, the number of seconds left to wait before the request can be repeated"""


@dataclass
class Response:
    ok: bool
    # ok == True:
    result: Optional[dict] = None
    # ok == False:
    description: Optional[str] = None
    error_code: Optional[int] = None
    parameters: Optional[ResponseParameters] = None

    def __init__(self, raw: dict):
        self.ok = raw["ok"]
        self.result = raw.get("result")
        self.description = raw.get("description")
        self.error_code = raw.get("error_code")
        self.parameters = raw.get("parameters")


@dataclass
class MyTelegram:
    config: Config
    client: AsyncClient
    CHAT_ID: int

    def __init__(self, chat_id: int = OWNER_ID):
        self.config = config = Config(chat_id)
        self.client = AsyncClient(
            base_url=f"https://api.telegram.org/bot{config._BOT_TOKEN}/"
        )
        self.CHAT_ID = chat_id

    async def _init(self):
        await self.config.load_values()
    
    # @repeat_until_complete
    async def _invoke(self, path: str, data: dict) -> Response:
        repeat_post = repeat_until_complete(self.client.post)
        request = await repeat_post(path, json=data)
        response = request.json()
        result = Response(response)
        return result

    async def send_message(
        self, text: str, reply_to_message_id: Optional[int] = None
    ) -> TgMessage | Response:

        response = await self._invoke(
            "sendMessage",
            dict(
                chat_id=self.CHAT_ID,
                text=text,
                reply_to_message_id=reply_to_message_id,
                parse_mode="HTML",
            ),
        )
        # logger.info(f"{response=}")
        if response.ok and (msg := response.result):
            msg["from_user"] = msg["from"]
            del msg["from"]
            msg["id"] = msg["message_id"]
            del msg["message_id"]
            message = TgMessage(**msg)
            return message
        else:
            return response

    async def send_text(self, text) -> TgMessage | Response:
        msg = await self.send_message(text)
        # logger.info(f"{msg=}")
        return msg

    async def reply_text(self, msg_id: int | None, text: str) -> TgMessage | Response:
        msg = await self.send_message(text, reply_to_message_id=msg_id)
        return msg

    async def stop(self):
        await self.send_message("Бот остановлен.")
