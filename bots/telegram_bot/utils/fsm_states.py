from aiogram.fsm.state import State, StatesGroup


class CommonStates(StatesGroup):
    START = State()
    MENU = State()


class EchoStates(StatesGroup):
    MENU = State()
    ECHO = State()


class BotStates(StatesGroup):
    MENU = State()
    SETTINGS = State()
    START_POLLING = State()


class SettingStates(StatesGroup):
    MENU = State()
    
