from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core import strings
from app.core.logging import logger
from app.db.session import get_db
from app.services import user, whatsapp

from . import states
from .client import DP
from .common import (
    select_contecs,
    require_login,
    require_user,
    send_message_prosess,
)
from .utils import get_chat_context


@DP.message(Command("start"))
async def start(message: Message):
    _, chat_id = get_chat_context(message)
    async with get_db() as session:
        await user.add_user(session, chat_id)
    await message.reply(strings.Messages.Home)


@DP.message(Command("help"))
async def help(message: Message):
    await message.reply(strings.Messages.Help)


@DP.message(Command("commands"))
async def commands(message: Message):
    await message.reply(strings.Messages.Commands)


@DP.message(Command("support"))
async def support(message: Message):
    await message.reply(strings.Messages.Support)


@DP.message(Command("login"))
@require_user
async def login(message: Message, state: FSMContext):
    await state.set_state(states.LoginWhatsapp.ENTER_NUMBER)
    await message.reply(strings.Messages.Enter_Phonenumber)


@DP.message(Command("login_status"))
@require_user
@require_login
async def login_status(message: Message):
    msg = await message.reply(strings.Messages.Wait)
    async with get_db() as session:
        qu_res = await user.get_identifiers(session, message.chat.id)
        identifier = qu_res.first()
    async with whatsapp.build_connector(identifier.phone) as connector:
        if isinstance(connector, whatsapp.wa.WhatsAppConnected):
            await msg.edit_text(strings.Messages.Connected)
        else:
            await msg.edit_text(strings.Messages.Disconnected)


@DP.message(Command("send"))
@require_user
@require_login
async def send(message: Message, state: FSMContext):
    await state.set_state(states.SendMessage.SELECT)
    await state.update_data({"data": states.DataSendMessage()})
    msg = await message.reply(strings.Messages.Wait)
    try:
        await select_contecs(message, states.DataSendMessage())
    except AttributeError as e:
        logger.error(f"Failed Show Contacts Select : {e}")
        await msg.edit_text(strings.Messages.Error_Retry)
        return

    


@DP.message(states.SendMessage.SEND, Command("confirm"))
async def start_send(message: Message, state: FSMContext):
    msg = await message.answer(strings.Messages.Wait)
    return await send_message_prosess(msg, state)
