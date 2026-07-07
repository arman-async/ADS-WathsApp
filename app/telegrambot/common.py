import asyncio
import tempfile
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from random import randint
from typing import AsyncGenerator, Union

import nio
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app import services
from app.core import strings
from app.core.logging import logger
from app.db.models import Identifier
from app.db.session import get_db
from app.models.contacts import Contact
from app.services import whatsapp as wa_service

from . import states, ui
from .utils import extract_file_id, get_chat_context, get_extension_file


def extract_update(*args, **kwargs) -> Union[Message, CallbackQuery]:
    """
    Finds the first argument that is an instance of Message or CallbackQuery.
    """
    for arg in args:
        if isinstance(arg, (Message, CallbackQuery)):
            return arg
    for val in kwargs.values():
        if isinstance(val, (Message, CallbackQuery)):
            return val
    raise ValueError("No Message or CallbackQuery found in arguments")


# ===================================
#              USER CHECK
# ===================================
async def user_exists_in_db(update: Union[Message, CallbackQuery]) -> bool:
    _, chat_id = get_chat_context(update)
    async with get_db() as session:
        user = await services.user.get_user(session, chat_id)
    if user:
        return True
    return False


def require_user(func):
    """
    Decorator that ensures the user exists in the database.

    Extracts the update from arguments and checks for the user's presence.
    If the user is not found, replies with a registration prompt and halts execution.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        update = extract_update(*args, **kwargs)
        message, chat_id = get_chat_context(update)
        if not (await user_exists_in_db(update)):
            logger.info(f"User {chat_id} is not registered")
            await message.answer(strings.Messages.First_Start)
            return
        logger.info(f"User {chat_id} is registered")
        return await func(*args, **kwargs)

    return wrapper


# ===================================
#              LOGIN CHECK
# ===================================
async def login_exists_in_db(update: Union[Message, CallbackQuery]) -> bool:
    _, chat_id = get_chat_context(update)
    async with get_db() as session:
        accounts = await services.user.get_identifiers(session, chat_id)
        account = accounts.first()
    if account:
        return True
    return False


def require_login(func):
    """
    Decorator that verifies if the user has an active session or logged-in account.

    Extracts the update from arguments and checks for associated identifiers.
    If no active account is found, replies with a login prompt and halts execution.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        update = extract_update(*args, **kwargs)
        message, chat_id = get_chat_context(update)
        if not (await login_exists_in_db(update)):
            logger.info(f"User {chat_id} is not logged-WA in")
            await message.answer(strings.Messages.First_Login)
            return
        logger.info(f"User {chat_id} is logged-WA in")
        return await func(*args, **kwargs)

    return wrapper


@asynccontextmanager
async def get_connector(
    update: Union[Message, CallbackQuery],
) -> AsyncGenerator[wa_service.wa.WhatsAppConnected | None, None]:
    _, chat_id = get_chat_context(update)

    async with get_db() as session:
        accounts = await services.user.get_identifiers(session, chat_id)
        account = accounts.first()

    if not isinstance(account, Identifier):
        logger.warning(f"User {chat_id} is not logged-WA in")
        yield None
        return

    async with services.whatsapp.build_connector(account.phone) as connector:
        yield connector


@require_user
async def get_ws_group_inline_but(
    update: Union[Message, CallbackQuery],
    state_data: states.DataSendMessage,
) -> ui.InlineKeyboardMarkup:
    message, chat_id = get_chat_context(update)

    async with get_db() as session:
        accounts = await services.user.get_identifiers(session, chat_id)
        account = accounts.first()
    if not isinstance(account, Identifier):
        logger.warning(f"User {chat_id} is not logged-WA in")
        return await message.answer(strings.Messages.First_Login)

    async with get_connector(update) as connector:
        contacts_group, _ = await services.whatsapp.get_groups(connector)

        return ui.list_contacts(
            items=tuple(
                Contact(
                    id=contact.room_id,
                    name=contact.display_name,
                )
                for contact in contacts_group
            ),
            selected=state_data.selected_contacts,
            selected_all=state_data.select_all,
        )


async def send_message(
    connector: wa_service.wa.WhatsAppConnected,
    room: nio.MatrixRoom,
    message: Message,
    bot: Bot,
):
    logger.info(f"Start Sending message: {message.message_id}")

    if message.text:
        logger.info(f"Sending text: {message.text}")
        await wa_service.send_text(connector, room, message.text)
        return

    file_id = extract_file_id(message)
    extension = get_extension_file(message)
    cache_path = Path(tempfile.gettempdir()) / f"{file_id}{extension}"

    logger.info(f"Downloading file: {message.message_id},{extension}")
    logger.debug(f"- file_id: {file_id}, extension: {extension}")

    if not cache_path.exists():
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, cache_path)

    logger.debug(f"Sending file: {cache_path}")
    logger.info(f"Sending file: {message.message_id},{extension}")

    caption = message.caption or ""
    await wa_service.send_media(connector, room, cache_path, caption)


async def sleep_stream_message(
    message: Message,
    sleep_time: int,
    reply_markup: InlineKeyboardMarkup = None,
    text: str = "",
):
    for sec in range(1, sleep_time + 1):
        await asyncio.sleep(1)
        try:
            await message.edit_text(f"{text} {sec}/{sleep_time}")
            if reply_markup:
                await message.edit_reply_markup(reply_markup)
        except TelegramBadRequest:
            pass


async def send_message_prosess(
    update: Union[Message, CallbackQuery], state: FSMContext
):
    data: states.DataSendMessage = (await state.get_data()).get("data")
    await state.clear()
    msg, _ = get_chat_context(update)
    async with get_connector(update) as connector:
        if not isinstance(connector, services.whatsapp.wa.WhatsAppConnected):
            await msg.edit_text(strings.Messages.Disconnected)
            return

        if data.select_all:
            all_groups = await services.whatsapp.get_groups(connector=connector)
            chat_list = [
                connector.client.rooms.get(dialog.room_id)
                for dialog in all_groups[0]
            ]
        elif data.selected_contacts:
            chat_list = [
                connector.client.rooms.get(room_id)
                for room_id in data.selected_contacts
            ]
        
        for do, chat in enumerate(chat_list, start=1):
            for do_msg, message in enumerate(data.messages, start=1):
                await msg.edit_text(
                    strings.Messages.Send_Prosess.format(
                        sent_chats=do,
                        total_chats=len(chat_list),
                        sent_messages_in_chat=do_msg,
                        total_messages_in_chat=len(data.messages),
                    )
                )
                if not isinstance(message, Message):
                    continue
                await send_message(connector, chat, message, update.bot)
                await sleep_stream_message(
                    msg,
                    data.interval_mode.send_message,
                    text=strings.Messages.Send_Prosess.format(
                        sent_chats=do,
                        total_chats=len(chat_list),
                        sent_messages_in_chat=do_msg,
                        total_messages_in_chat=len(data.messages),
                    )
                    + "\n\n"
                    + strings.Messages.Wait,
                )
            await sleep_stream_message(
                msg,
                randint(data.interval_mode.start_range, data.interval_mode.end_range),
                text=strings.Messages.Send_Prosess.format(
                    sent_chats=do,
                    total_chats=len(chat_list),
                    sent_messages_in_chat=do_msg,
                    total_messages_in_chat=len(data.messages),
                )
                + "\n\n"
                + strings.Messages.Wait,
            )
    await msg.edit_text(strings.Messages.Send_Prosess_End)
