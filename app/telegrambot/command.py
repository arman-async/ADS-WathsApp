from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core import strings
from app.core.logging import logger
from app.db.session import get_db
from app.services import banner, user, whatsapp
from app.telegrambot import ui

from . import states
from .client import DP
from .common import (
    require_login,
    require_user,
    select_contecs,
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
    try:
        async with whatsapp.get_connector(identifier.phone) as connector:
            if isinstance(connector, whatsapp.wa.WhatsAppConnected):
                await msg.edit_text(strings.Messages.Connected)
            else:
                await msg.edit_text(strings.Messages.Disconnected)
    except Exception as e:
        logger.error(f"Failed Login Status : {e}")
        await msg.edit_text(strings.Messages.Disconnected)


@DP.message(Command("send"))
@require_user
@require_login
async def send(message: Message, state: FSMContext):
    await state.set_state(states.SendMessage.SELECT)
    await state.update_data({"data": states.DataSendMessage()})
    msg = await message.reply(strings.Messages.Wait)
    try:
        await select_contecs(msg, states.DataSendMessage())
    except Exception as e:
        logger.error(f"Failed Show Contacts Select : {e}")
        await msg.edit_text(strings.Messages.Disconnected)
        return


@DP.message(Command("send_smart"))
@require_user
@require_login
async def send_continuous(message: Message, state: FSMContext):
    _, chat_id = get_chat_context(message)
    message = await message.answer(strings.Messages.Wait)
    # Show Banner And Temp Methode
    async with get_db() as session:
        banners_in_db = await banner.get_banners(session, chat_id)
    banners = []
    if banners_in_db:
        banners = [(b.id, b.name) for b in banners_in_db]

    await state.set_state(states.ContinuousMessageSending.CHOICE)
    await message.edit_text(
        "بنر مورد نظر را انتخاب کنید یا از طریق ارسال مستقیم همین حالا پیام های خود را بفرستید"
    )
    await message.edit_reply_markup(
        reply_markup=ui.choice_banner_or_temp(banners=banners)
    )


@DP.message(states.SendMessage.SEND, Command("confirm"))
async def start_send(message: Message, state: FSMContext):
    msg = await message.answer(strings.Messages.Wait)
    return await send_message_prosess(msg, state)
