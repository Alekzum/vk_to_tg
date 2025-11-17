from aiogram.fsm.state import State, StatesGroup


class CommonStates(StatesGroup):
    START = State()
    MENU = State()


class EchoStates(StatesGroup):
    MENU = State()
    ECHO = State()


class BotStates(StatesGroup):
    class Answer(StatesGroup):
        SEND_MESSAGE = State()
        ADD_MEDIA = State()
        LOADING_CHATS = State()
        CHOOSE_CHAT = State()
        MAYBE_CHOOSE_CHAT = State()
    MENU = State()
    # SETTINGS = State()
    START_POLLING = State()
    # ANSWER = State()
    # CHOOSE_CHAT = State()


class SettingStates(StatesGroup):
    class Blacklist(StatesGroup):
        SELECT = State()
        CONFIRM = State()
    MENU = State()
    
