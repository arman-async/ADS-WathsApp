import asyncio
import math
import tempfile
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from random import choice, choices, randint, uniform
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
            logger.info(f"User {chat_id} is not regestered-WA in")
            await message.answer(strings.Messages.First_Login)
            return
        logger.info(f"User {chat_id} is regestered-WA in")
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
        logger.warning(f"User {chat_id} is not regestered-WA in")
        yield None
        return

    async with services.whatsapp.get_connector(account.phone) as connector:
        yield connector


@require_user
async def select_contecs(
    update: Union[Message, CallbackQuery],
    state_data: states.DataSendMessage,
    page_size: int = 5,
):
    message, chat_id = get_chat_context(update)

    async with get_db() as session:
        accounts = await services.user.get_identifiers(session, chat_id)
        account = accounts.first()
    if not isinstance(account, Identifier):
        logger.warning(f"User {chat_id} is not regestered-WA in")
        return await message.answer(strings.Messages.First_Login)

    async with get_connector(update) as connector:
        await message.edit_text(strings.Messages.Syncing + "\n" + strings.Messages.Wait)
        await services.whatsapp.sync_contacts(connector)
        contacts_group, total = await services.whatsapp.get_groups(connector)

        keyboard = ui.list_contacts(
            items=tuple(
                Contact(
                    id=contact.room_id,
                    name=contact.display_name,
                )
                for contact in contacts_group
            ),
            selected=state_data.selected_contacts,
            selected_all=state_data.select_all,
            selected_rand=state_data.select_random,
            page_size=page_size,
            page=state_data.page,
        )
    await message.edit_text(
        strings.Messages.Select_Contact.format(
            total=total,
            page_now=state_data.page + 1,
            page_total=math.ceil(len(contacts_group) / page_size),
            select_total=total
            if state_data.select_all
            else len(state_data.selected_contacts),
        )
    )
    await message.edit_reply_markup(reply_markup=keyboard)


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
            await message.edit_text(
                f"{text} {sec}/{sleep_time}", reply_markup=reply_markup
            )

        except TelegramBadRequest:
            pass


async def send_message_prosess(
    update: Union[Message, CallbackQuery], state: FSMContext
):

    async def is_trminat() -> bool:
        if (await state.get_state()) == states.SendMessage.RUNING:
            return False
        return True

    data: states.DataSendMessage = (await state.get_data()).get("data")
    msg, _ = get_chat_context(update)
    async with get_connector(update) as connector:
        if not isinstance(connector, services.whatsapp.wa.WhatsAppConnected):
            await msg.edit_text(strings.Messages.Disconnected)
            return

        await msg.edit_text(strings.Messages.Syncing + "\n" + strings.Messages.Wait)
        all_groups = (await services.whatsapp.get_groups(connector=connector))[0]

        chat_list = []
        if data.select_all:
            chat_list = [
                connector.client.rooms.get(dialog.room_id) for dialog in all_groups
            ]
        elif data.selected_contacts:
            chat_list = [
                connector.client.rooms.get(room_id)
                for room_id in data.selected_contacts
            ]

        if (not chat_list) and (data.select_random is False):
            await msg.edit_text(
                "شما هیچ مخاطب (گروهی) را برای ارسال انتخاب نکردید - لیست ارسال خالی است "
            )
            return

        repet_round = 5 if data.repet_min else 1
        for repet_round_now in range(1, repet_round + 1):
            if await is_trminat():
                await msg.edit_text("متوقف شد")
                return
            chat_list = [
                connector.client.rooms.get(choice(all_groups).room_id)
                for _ in range(int(len(all_groups) / 2))
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
                    if await is_trminat():
                        await msg.edit_text("متوقف شد")
                        return
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
                        reply_markup=ui.cancel(),
                    )
                await sleep_stream_message(
                    msg,
                    randint(
                        data.interval_mode.start_range, data.interval_mode.end_range
                    ),
                    text=strings.Messages.Send_Prosess.format(
                        sent_chats=do,
                        total_chats=len(chat_list),
                        sent_messages_in_chat=do_msg,
                        total_messages_in_chat=len(data.messages),
                    )
                    + "\n\n"
                    + strings.Messages.Wait,
                    reply_markup=ui.cancel(),
                )
            if await is_trminat():
                await msg.edit_text("متوقف شد")
                return
            if data.repet_min:
                await sleep_stream_message(
                    msg,
                    data.repet_min,
                    text=f"در حال حاضر {repet_round_now} دور پیام ارسال کردیم"
                    + "\n"
                    + "دور بعدی ارسال پیام ",
                    reply_markup=ui.cancel(),
                )
    await msg.edit_text(strings.Messages.Send_Prosess_End)


async def continuous_message_sending(
    update: Union[Message, CallbackQuery], state: FSMContext
):
    msg, _ = get_chat_context(update)
    delays = {
        0: (0.5, 1, 10, 15, 30, 45, 60, 75),
        1: (0.7, 2, 20, 25, 50, 75, 100, 125),
        2: (0.9, 4, 25, 40, 60, 80, 100, 130),
        3: (1.5, 5, 30, 60, 120, 180, 240, 300),
    }
    weights = [10, 15, 17, 15, 15, 15, 8, 5]
    interval_mode = int((await state.get_data()).get("interval"))

    def get_interval() -> float:
        a = choices(delays[interval_mode], weights=weights, k=1)[0]
        b = choices(delays[interval_mode], weights=weights, k=1)[0]
        return uniform(float(min(a, b)), float(max(a, b)) + 0.25)

    async def check_termination() -> bool:
        run_state = await state.get_state()
        if run_state == states.ContinuousMessageSending.STOP:
            return True
        return False

    async def get_random_chat() -> nio.MatrixRoom:
        async with get_connector(update) as connector:
            all_groups, _ = await wa_service.get_groups(connector)
            dilog = choice(all_groups)
            return connector.client.rooms.get(dilog.room_id)
        
    async def get_random_message() -> Message:
        messages = (await state.get_data()).get("messages")
        return choice(messages)

    counter_sent_message = 0
    while True:
        if await check_termination():
            await msg.edit_text(strings.Messages.Canceled)
            return
        chat = await get_random_chat()
        message = await get_random_message()
        async with get_connector(update) as connector:
            await send_message(connector, chat, message, update.bot)
            counter_sent_message += 1
        await sleep_stream_message(
            msg,
            get_interval(),
            text=strings.Messages.Send_Prosess_Continue.format(
                sent_messages=counter_sent_message
            )
            + "\n"
            + strings.Messages.Wait,
            reply_markup=ui.cancel(),
        )
