from datetime import datetime
from colorama import Fore, Style
from textwrap import dedent
import dotenv
import httpx
import time
import main
import json
import sys
import os
import re


nl = "\n"


def colored(text, color):
    if not main.colored_text:
        return text
    else:
        color = color.upper()
        colors = {"LIGHT_BLUE": "LIGHTBLUE_EX"}
        color = colors[color] if color in colors else color
        result = eval(f'Fore.{color}') + text + Style.RESET_ALL
        return result

def load_raw():
    with open('config.json', encoding="utf-8") as f:
        raw = json.load(f)
        return raw


def save_raw(raw):
    with open('config.json', 'w', encoding="utf-8") as f:
        return json.dump(raw, f)


def file_append(text):
    with open("logs.txt", "a", encodings="utf-8") as file: file.writelines(text)


class Config():
    def __init__(self):
        self.re_find_token = re.compile("access_token=([^&]+)")
        self.load()

    def __str__(self):
        return f"""<{self.chat_id=}>"""

    def load(self):
        # Создаём/извлекаем конфигурацию с .env файлом
        self.dot_env_file = ""
        if "config.json" in os.listdir():
            try:
                with open("config.json", encoding="utf-8") as _file:
                    self.config = json.load(_file)
                self.dot_env_file = self.config["env_file"]
            except KeyError:
                pass
            except json.JSONDecodeError:
                pass

        if not self.dot_env_file:
            self.dot_env_file = input("Введите название файла с переменными (по умолчанию .env; примеры: .env или env/.env):")
            self.dot_env_file = self.dot_env_file if self.dot_env_file else ".env"

            _config = {"env_file": self.dot_env_file, "messages": {}}
            with open("config.json", "w", encoding="utf-8") as _file:
                json.dump(_config, _file, ensure_ascii=False)

            with open(self.dot_env_file, "w", encoding="utf-8") as _file:
                _file.writelines("")


        with open("config.json", encoding="utf-8") as _file:
            self.cfg = self.raw = json.load(_file)
        self.env_in_dirs = dotenv.load_dotenv(self.dot_env_file, verbose=True)
        # Пытаемся получить нужные АПИ

        self.bot_api = dotenv.get_key(self.dot_env_file, "BOT_API")
        self.chat_id = dotenv.get_key(self.dot_env_file, "CHAT_ID")
        self.access_token = dotenv.get_key(self.dot_env_file, "ACCESS_TOKEN")

        if not self.bot_api:
            self.bot_api = input("Введите токен своего бота (может быть найден у https://t.me/botfather): ")
            dotenv.set_key(self.dot_env_file, "BOT_API", self.bot_api)

        if not self.chat_id:
            self.chat_id = input("Введите ваш id в телеграм (https://t.me/my_id_bot в помощь): ")
            dotenv.set_key(self.dot_env_file, "CHAT_ID", self.chat_id)

        if not self.access_token:
            self.access_token = input("Введите ссылку из адресной строки по ссылке https://vk.cc/a6dCgm: ")
            self.access_token = self.re_find_token.findall(self.access_token)[0]
            dotenv.set_key(self.dot_env_file, "ACCESS_TOKEN", self.access_token)


class Telegram():
    def __init__(
        self, chat_id: int, token: str, disable_notification: bool = False
    ):
        self.chat_id = chat_id
        self.disable_notification = disable_notification
        self.telegram_base_url = f"https://api.telegram.org/bot{token}/"
        
        self._client = httpx.Client(base_url=self.telegram_base_url)
    
    def post(self, *args, **kwargs):
        done = False
        while not done:
            try:
                request = self._client.post(*args, **kwargs)
            except:
                time.sleep(1)
            else:
                done = True
        
        return request
    
    def send(self, message: str, push=False) -> dict:
        request = self.post(
            url="sendMessage",
            data={
                "chat_id": self.chat_id,
                "text": dedent(message),
                "parse_mode": "HTML"
            }
        ).json()
        return request

    def reply(self, reply_to_id: int, message: str) -> dict:
        """Reply to some message. reply_to_id from Telegram"""
        request = self.post(
            url="sendMessage",
            data={
                "chat_id": self.chat_id,
                "reply_parameters": json.dumps({"message_id": reply_to_id}),
                "text": dedent(message),
                "parse_mode": "HTML"
            }
        ).json()
        return request


config = Config()
tg_bot = Telegram(config.chat_id, config.bot_api)


user_cache = {}
group_cache = {}
chat_cache = {}


def action_to_string(action: dict):
    type = action['type']
    
    if action.get('member_id') or action.get('email'):
        display_name = action.get('email', getUserName(action['member_id']))
    
    match type:
        case 'chat_photo_update':  # обновлена фотография беседы
            result = f"Обновил фото беседы"
        
        case 'chat_photo_remove':  # удалена фотография беседы        
            result = f"Убрал фото беседы"
        
        case 'chat_create':  # создана беседа        
            result = f"Создал беседу с названием «{action['text']}»"
        
        case 'chat_title_update':  # обновлено название беседы        
            result = f"Изменил название беседы на «{action['text']}»"
        
        case 'chat_invite_user':  # приглашен пользователь        
            result = f"Приглашен {display_name}"
        
        case 'chat_kick_user':  # исключен пользователь        
            result = f"Выгнан {display_name}"
        
        case 'chat_pin_message':  # закреплено сообщение        
            result = f"Закрепил сообщение"
        
        case 'chat_unpin_message':  # откреплено сообщение        
            result = f"Открепил сообщение"
        
        case 'chat_invite_user_by_link':  # пользователь присоединился к беседе по ссылке.
            result = f"Зашёл в беседу по ссылку"

        case _:
            result = "•NaN•"
            print(action)
    return result


def get_url(obj: dict):
    type = obj['type']
    try:
        match obj:
            case {"photo": photo} if type == 'photo':
                sizes = sorted(photo.get('sizes', []), key=lambda x: x['height'], reverse=True)
                for photik in sizes:
                        if photik['type'] in ['w', 'z', 'x']:
                            url = photik['url']
                            break
                else:
                    print(sizes, f"\ndidn't get sizes ['w', 'z', 'x']")
                    owner_id, id = photo.get('owner_id', "???"), photo.get('id', "???")
                    url = f"https://vk.com/{type}" + f"{owner_id}_{id}"

            case {'video': video} if type == 'video':
                owner_id, id = video['owner_id'], video['id']
                url = video['player']

            case {'audio': audio} if type == 'audio':
                url = audio['url']

            case {'doc': doc} if type == 'doc':
                url = doc['url']
                type = doc['title'] + "(document)"

            case {'market': market} if type == 'market':
                url = 'Артикул: ' + market['sku']

            case {'market_album': market_album} if type == 'market_album':
                url = f"Название: {market_album['title']}, id владельца: {market_album['owner_id']}"

            case {'wall_reply': wall_reply} if type == 'wall_reply':
                url = f"№{wall_reply['id']} от пользователя №{wall_reply['owner_id']}"

            case {'sticker': sticker} if type == 'sticker':
                url = sticker['images'][-1]['url']

            case {'gift': gift} if type == 'gift':
                url = gift['thumb_256']

            case {'audio_message': audio_message} if type == 'audio_message':
                url = audio_message['link_mp3']
            
            case {'wall': wall} if type == "wall":
                url = f"https://vk.com/wall{wall['from_id']}_{wall['id']}"
            
            case {'link': link} if type == "link":
                url = link['url']

            case _:
                url = "•NaN•"
                print(obj)
        return url, type
    except:
        print(obj)
        raise


def message_to_str2(message, include_reply=True, include_fwd=True) -> tuple[str, str, bool]:
    at = datetime.fromtimestamp(message.get('date')).strftime('%H:%M:%S')    

    text = message.get('text')
    forwarded_msg = nc_forwarded_msg = ""

    to_add = []
    if message.get('action'):
        action_str = action_to_string(message['action'])
        to_add.append(action_str)
        
    if len(message.get('attachments')) > 0:
        for attachment in message.get('attachments'):
            url, type_str = get_url(attachment)
            to_add.append(f"<a href='{url}'>{type_str}</a>")
    
    to_add = ("\n *" + ", ".join(to_add)) if to_add else ""
    
    rply_msg = message.get("reply_message")
    if rply_msg and include_reply:
        prev_msg, nc_prev_msg, _ = message_to_str2(
            message=rply_msg,
        )

        prev_msg = f"""{prev_msg}\n░└"""
        nc_prev_msg = f"""{nc_prev_msg}\n░└"""

    else:
        nc_prev_msg = prev_msg = ""

    # print(message)
    if include_fwd and message.get('fwd_messages'):
        for fwd_message in message['fwd_messages']:
            forwarded_msg, nc_forwarded_msg, _ = message_to_str2(
                message=fwd_message
            )
            
            forwarded_msg = "*Forwarded message:\n{}\n".format(forwarded_msg.replace('\n', '\n│░'))
            nc_forwarded_msg = "\n*Forwarded message:\n│░{}\n".format(nc_forwarded_msg.replace('\n', '\n│░'))

    nc_prep_time = f"[{at}] "
    prep_time = colored(nc_prep_time, 'light_blue')

    nc_user_ask = getUserName(message['from_id'])
    user_ask = colored(nc_user_ask, 'red')

    nc_prep_text = text + to_add
    prep_text = colored(text, 'cyan') + to_add

    if message.get('peer_id') is not None and message.get('peer_id') > 2000000000:
        nc_conversation = getChatName(message['peer_id'])
        mark = ""
    elif message.get('peer_id') is not None:
        nc_conversation = getUserName(message['peer_id'])
        mark = "[ЛС] "
    else:
        nc_conversation = "*None*"
        mark = ""
    conversation = colored(nc_conversation, 'green')

    info_conversation = prep_time + mark + f"[{conversation} / {user_ask}]: {prep_text}"
    nc_info_conversation = nc_prep_time + mark + f"[{nc_conversation} / {nc_user_ask}]: {nc_prep_text}"


    output = "".join([prev_msg, info_conversation, forwarded_msg])
    nc_output = "".join([nc_prev_msg, nc_info_conversation, nc_forwarded_msg])
    in_blacklist = nc_conversation in main.blacklist
    # print(nc_output)
    return output, nc_output, in_blacklist


def worker(event, api):
    global getUserName
    global getGroupName
    global getChatName
    # User
    def getUserName(user_id):
        global user_cache
        user = user_cache.get(user_id)
        if user is None:
            if user_id < 0:
                return getGroupName(abs(user_id))
            user_cache[user_id] = user
            user = api.users.get(user_ids=user_id)[0]
        return f"{user['first_name']} {user['last_name']}"


    # group
    def getGroupName(group_id):
        global group_cache
        group = group_cache.get(group_id)
        if group is None:
            group = api.groups.getById(group_id=(abs(group_id)))[0]
            group_cache[group_id] = group
        return group['name']


    # Chat
    def getChatName(chat_id):
        global chat_cache
        chat = chat_cache.get(chat_id)
        if chat is None:
            chat = api.messages.getChatPreview(peer_id=chat_id)
            chat_cache[chat_id] = chat
        return chat['preview']['title']
    
    globals()['api'] = api
    message = api.messages.getById(message_ids=event.message_id)['items'][0]

    colored_output, output, in_blacklist = message_to_str2(message)

    print(output or colored_output)
    main.file_logger.info(output)

    raw = load_raw()
    
    if not in_blacklist:
        if 'reply_message' in message and str(message["reply_message"]["id"]) in raw['messages']:
            tg_msg = tg_bot.reply(
                int(raw['messages'][str(message["reply_message"]["id"])]), 
                output
            )
        else:
            tg_msg = tg_bot.send(output)
        vk_id = event.message_id
        raw['messages'].update({vk_id: tg_msg['result']['message_id']})
        save_raw(raw)

if __name__ == "__main__":
    Config()
