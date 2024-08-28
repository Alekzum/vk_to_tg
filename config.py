from dataclasses import dataclass
from typing import Literal
import dotenv
import json
import re
import os


CHATS_BLACKLIST = [
    '🚖🚕Такси "Ладья"🚕🚖', 118
]


DB_NAME = "data{os.sep}database.db"
re_find_token = re.compile(r"access_token=([^&]+)")
configIsHere = "config.json" in os.listdir("data")


@dataclass
class MyConfig:
    dot_env_file: str
    """File with "secret" variables (aka .env file)"""

    api_key: str
    """For telegram bot"""

    bot_token: str
    """For telegram bot"""

    chat_id: int
    """Chat id, where telegram bot will send messages (deprecated?)"""

    access_token: str
    """For vkontakte"""
    
    def __init__(self):
        if not configIsHere:
            self.create_config()
        
        self.dot_env_file = MyConfig.get_config_name()
        
        self.api_id = dotenv.get_key(self.dot_env_file, "api_id") or self.update_variable("api_id")
        self.api_hash = dotenv.get_key(self.dot_env_file, "api_hash") or self.update_variable("api_hash")
        self.bot_token = dotenv.get_key(self.dot_env_file, "bot_token") or self.update_variable("bot_token")
        self.chat_id = int(dotenv.get_key(self.dot_env_file, "chat_id") or self.update_variable("chat_id"))
        self.access_token = dotenv.get_key(self.dot_env_file, "access_token") or self.update_variable("access_token")

    def __str__(self):
        return f"""<Config {self.chat_id=}"""

    def __repr__(self):
        return f'''utils.classes.Config(dot_env_file={self.dot_env_file!r}, api_id={self.api_id!r}, , api_key={self.api_hash!r}, bot_token={self.bot_token!r}, chat_id={self.chat_id!r}, access_token={self.access_token!r})'''
    
    def create_config(self):
        dot_env_file = input('Введите название файла с переменными (по умолчанию ".env". Примеры: ".env" или "env/.env" (без кавычек)):')
        self.dot_env_file = dot_env_file or ".env"

        with open(f"data{os.sep}config.json", "w", encoding="utf-8") as _file:
            json.dump({"env_file": dot_env_file}, _file, ensure_ascii=False)

        with open(dot_env_file, "w", encoding="utf-8") as _file:
            _file.writelines("")
        self.update_variable("all")
    
    @staticmethod
    def get_config_name() -> str:
        with open(f"data{os.sep}config.json", encoding="utf-8") as _file:
            raw = json.load(_file)
        config = raw['env_file']
        return config
    
    def update_variable(self, variable_name: Literal["api_id", "api_hash", "bot_token", "chat_id", "access_token", "all"]):
        dot_env_file = self.dot_env_file
        match variable_name:
            case "api_id":
                self.api_id = input("Введите api_id (может быть найден на странице https://t.me/botfather): ")
                dotenv.set_key(dot_env_file, "api_id", self.api_id)
                return self.api_id
            
            case "api_hash":
                self.api_hash = input("Введите API_HASH (может быть найден на странице https://t.me/botfather): ")
                dotenv.set_key(dot_env_file, "API_HASH", self.api_hash)
                return self.api_hash
            
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

            case "all":
                [self.update_variable(v) for v in ("bot_token", "chat_id", "access_token")]

Config = MyConfig()