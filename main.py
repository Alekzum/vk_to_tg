if __name__ == "__main__":
    import work
from vk_api.longpoll import VkLongPoll, VkEventType
from threading import Thread
from importlib import reload
import traceback, logging, vk_api


colored_text = True
blacklist = ['🚖🚕Такси "Ладья"🚕🚖']

# Логи
log_file = "log.txt"

# INFO WARN WARNING
FORMAT = '%(asctime)s - %(levelname)s (%(name)s) %(message)s'

console_logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
console_logger.addHandler(stream_handler)
console_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file, encoding='utf8')
file_logger = logging.getLogger("log.txt")
file_logger.addHandler(file_handler)

if __name__ == "__main__":
    logging.basicConfig(format=FORMAT)

    config = work.Config()
    tg_bot = work.Telegram(config.chat_id, config.bot_api)

    vk_session = vk_api.VkApi(token=config.access_token)
    api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session, wait=5)
    owner_id = api.users.get()[0]['id']
    

    console_logger.info("Успешный запуск бота.")
    tg_bot.send("Успешный запуск бота.")
    
    # def invoke(*args, **kwargs):
        # tg_bot.send("closed with ctrl+enter")
        # raise KeyboardInterrupt

    # exit = keyboard.register_hotkey("ctrl+enter", invoke)

    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW:
                    work = reload(work)
                    multiprocess_worker = Thread(target=work.worker, args=(event,api))
                    multiprocess_worker.start()
        except Exception as ex:
            ex_str = traceback.format_exc()
            error_str = (f"Ошибка!\n" + "\n".join(ex_str.splitlines()[-4:]))[:4095]
            tg_bot.send(error_str)
            console_logger.error('\n'+ex_str+'\n')

        except KeyboardInterrupt:
            tg_bot.send("Бот выключен с помощью ctrl+c")
            console_logger.info("Бот выключен с помощью ctrl+c")
            raise
        