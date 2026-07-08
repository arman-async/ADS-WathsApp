from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core import strings
from app.core.logging import logger

from . import states, ui, utils
from .client import DP


@DP.message(states.LoginWhatsapp.ENTER_NUMBER, F.text)
async def lisener_wa_login_phone_number(message: Message, state: FSMContext):
    await state.update_data(number=message.text)
    await state.set_state(states.LoginWhatsapp.CONFIRM_NUMBER)
    await message.reply(strings.Messages.Confirm_or_Cancel, reply_markup=ui.confirm())


@DP.message(states.SendMessage.RESIVE)
async def resiver_messages(message: Message, state: FSMContext):
    data: states.DataSendMessage = (await state.get_data()).get("data")
    if (not utils.extract_file_id(message)) and (not message.text):
        logger.info(f"Drapped message: {message.message_id}")
        await message.delete()
        return

    data.messages.append(message)
    await state.update_data({"data": data})
    logger.info(f"Saved message: {message.message_id}")
    await message.reply(strings.Messages.Resevied_Message, reply_markup=ui.confirm())


@DP.message(states.ContinuousMessageSending.RESIVE)
async def resiver_messages_contin(message: Message, state: FSMContext):
    messages: list[Message] = (await state.get_data()).get("messages", list())
    if (not utils.extract_file_id(message)) and (not message.text):
        logger.info(f"Drapped message: {message.message_id}")
        await message.delete()
        return

    messages.append(message)
    await state.update_data({"messages": messages})
    logger.info(f"Saved message: {message.message_id}")
    await message.reply(strings.Messages.Resevied_Message, reply_markup=ui.confirm())