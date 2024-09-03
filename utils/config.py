from dataclasses import dataclass
from typing import Literal
import dotenv
import json
import re
import os


CHATS_BLACKLIST: list[str] = [
    '🚖🚕Такси "Ладья"🚕🚖'
]


re_find_token = re.compile(r"access_token=([^&]+)")
configIsHere = "config.json" in os.listdir("data")
configPath = os.sep.join(["data", "config.json"])


@dataclass
class MyConfig:
    bot_token: str
    """For telegram bot"""

    chat_id: int
    """Chat id, where telegram bot will send messages (deprecated?)"""

    access_token: str
    """For vkontakte"""

    need_update: bool
    """Do program needs to be updated or not"""

    dot_env_file: str = ".env"
    """File with "secret" variables (aka .env file)"""
    
    def __init__(self):
        self._entries = ["bot_token", "chat_id", "access_token", "need_update"]
        self.dot_env_file = ".env"
        
        self.bot_token = dotenv.get_key(self.dot_env_file, "bot_token") or self.update_variable("bot_token")
        self.chat_id = int(dotenv.get_key(self.dot_env_file, "chat_id") or self.update_variable("chat_id"))
        self.access_token = dotenv.get_key(self.dot_env_file, "access_token") or self.update_variable("access_token")
        self.need_update = (_t:=dotenv.get_key(self.dot_env_file, "need_update")) and bool(int(_t)) or self.update_variable("need_update")

    def __str__(self):
        return f"""<Config {self.chat_id=}"""

    def __repr__(self):
        return f'''utils.classes.Config({['{}={}'.format(n, getattr(self, n)) for n in self._entries]})'''
    
    def update_variable(self, variable_name: str | Literal["bot_token", "chat_id", "access_token", "need_update", "all"]):
        dot_env_file = self.dot_env_file
        match variable_name:            
            case "bot_token":
                self.bot_token = input("Введите токен своего бота (может быть найден у https://t.me/botfather): ")
                dotenv.set_key(dot_env_file, "bot_token", self.bot_token)
                return self.bot_token

            case "chat_id":
                chat_id = ""
                while not chat_id.isdecimal():
                    chat_id = input("Введите ваш id в телеграм (https://t.me/my_id_bot в помощь): ")
                self.chat_id = int(chat_id)
                dotenv.set_key(dot_env_file, "chat_id", str(self.chat_id))
                return self.chat_id

            case "access_token":
                access_token = input("Введите ссылку из адресной строки по ссылке https://vk.cc/a6dCgm: ")
                self.access_token = (re_find_token.findall(access_token) if not access_token.startswith("vk1.") else [access_token])[0]
                dotenv.set_key(dot_env_file, "access_token", self.access_token)
                return self.access_token
            
            case "need_update":
                need_update = ""
                while need_update.lower() not in ["y", "n"]:
                    need_update = input("Хотите получать обновления автоматически? (y/n): ").lower()
                self.need_update = True if need_update == "y" else False
                dotenv.set_key(dot_env_file, "need_update", str((int(self.need_update))))
                return self.need_update

            case "all":
                [self.update_variable(v) for v in self._entries]

Config = MyConfig()