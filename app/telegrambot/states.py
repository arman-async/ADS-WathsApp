from dataclasses import dataclass, field
from typing import List, NamedTuple

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message


class IntervalSendMessage(NamedTuple):
    start_range: int
    end_range: int
    send_message: int


@dataclass
class IntervalSendMessageMode:
    VEREY_FAST = IntervalSendMessage(1, 5, 1)
    FAST = IntervalSendMessage(1, 25, 2)
    NORMAL = IntervalSendMessage(1, 125, 3)
    SLOW = IntervalSendMessage(1, 300, 4)


@dataclass
class DataSendMessage:
    select_random: bool = False
    select_all: bool = False
    repet_min: int = 0
    selected_contacts: List[str] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    interval_mode: IntervalSendMessage = field(
        default_factory=lambda: IntervalSendMessageMode.NORMAL
    )
    page: int = 0


class SendMessage(StatesGroup):
    SELECT = State()
    RESIVE = State()
    SELECT_INTERVAL = State()
    SELECT_REPET = State()
    SEND = State()
    RUNING = State()
    STOP = State()
    data: DataSendMessage = DataSendMessage()


class LoginWhatsapp(StatesGroup):
    ENTER_NUMBER = State()
    CONFIRM_NUMBER = State()
    number: str


class ContinuousMessageSending(StatesGroup):
    RESIVE = State()
    SELECT_INTERVAL = State()
    RUNING = State()
    STOP = State()
    messages: list[Message] = []
    interval: int = 3
