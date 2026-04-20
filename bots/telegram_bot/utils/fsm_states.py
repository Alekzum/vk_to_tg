from aiogram.fsm.state import State, StatesGroup


class TGCommonStates(StatesGroup):
    START = State()
    MENU = State()


class TGEchoStates(StatesGroup):
    MENU = State()
    ECHO = State()


class VKBotStates(StatesGroup):
    class Answer(StatesGroup):
        SEND_MESSAGE = State()
        ADD_MEDIA = State()
        LOADING_CHATS = State()
        CHOOSE_CHAT = State()
        MAYBE_CHOOSE_CHAT = State()

    BEFORE_POLLING = State()
    # SETTINGS = State()
    POLLING = State()
    # ANSWER = State()
    # CHOOSE_CHAT = State()


class TGSettingStates(StatesGroup):
    class Blacklist(StatesGroup):
        SELECT = State()
        CONFIRM = State()

    class ApiKey(StatesGroup):
        SELECT = State()
        CONFIRM = State()

    MENU = State()
