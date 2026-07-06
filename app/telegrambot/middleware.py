import logging
from typing import Any
from typing import Dict
from typing import Callable
from typing import Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.types import CallbackQuery
from aiogram.types import TelegramObject


def get_event_info(event: TelegramObject) -> str:
    if isinstance(event, Message):
        return f"Message: {event.text or event.content_type}"
    if isinstance(event, CallbackQuery):
        return f"Callback: {event.data}"
    return f"Update: {type(event).__name__}"


class OuterLogging(BaseMiddleware):
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        user_id = user.id if user else "Unknown"
        info = get_event_info(event)

        self.logger.info(f"Outer | User: {user_id} | {info}")
        return await handler(event, data)


class InnerLogging(BaseMiddleware):
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        user_id = user.id if user else "Unknown"
        info = get_event_info(event)

        self.logger.info(f"Inner | User: {user_id} | Handler execution {info}")
        return await handler(event, data)
