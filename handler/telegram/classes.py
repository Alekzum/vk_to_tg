from utils.my_classes import Message
from dataclasses import dataclass
from typing import Optional

from utils.config import Config, MyConfig
from httpx import Client
import logging


logger = logging.getLogger(__name__)


@dataclass
class ResponseParameters:
    migrate_to_chat_id: Optional[int]
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
    app: Client
    chat_id: int
    config: MyConfig

    def __init__(self):
        self.config = Config
        self.client = Client(base_url=f"https://api.telegram.org/bot{Config.bot_token}/")
        self.chat_id = self.config.chat_id
    
    def _invoke(self, path: str, data: dict) -> Response:
        request = self.client.post(path, json=data)
        response = request.json()
        result = Response(response)
        return result
    
    def send_message(self, text: str, reply_to_message_id: Optional[int]=None) -> Message | Response:
        response = self._invoke("sendMessage", dict(chat_id=self.chat_id, text=text, parse_mode="HTML"))
        if response.ok and (msg:=response.result):
            msg["from_user"] = msg["from"]
            del msg["from"]
            msg["id"] = msg["message_id"]
            del msg["message_id"]
            message = Message(**msg)
            return message
        else:
            return response
    
    
    def send_text(self, text) -> Message | Response:
        msg = self.send_message(text)
        return msg
    
    def reply_text(self, msg_id: int, text: str) -> Message | Response:
        msg = self.send_message(text, reply_to_message_id=msg_id)
        return msg
    
    def stop(self):
        self.send_message("Бот остановлен.")
