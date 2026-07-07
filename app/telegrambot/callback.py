from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app import services
from app.core.strings import Messages
from app.db.session import get_db

from . import states, ui
from .client import DP
from .common import select_contecs, send_message_prosess
from .utils import get_chat_context


@DP.callback_query(F.data.startswith(ui.CallbackData.CANCEL))
async def cancel(callback: CallbackQuery, state: FSMContext):
    message, _ = get_chat_context(callback)
    await callback.answer(Messages.Wait)
    await state.clear()
    await message.edit_text(Messages.Canceled)


# =============================================
# Get WhatsAPP Login Code
# =============================================
@DP.callback_query(
    states.LoginWhatsapp.CONFIRM_NUMBER, F.data.startswith(ui.CallbackData.CONFIRM)
)
async def login_whatsapp(callback: CallbackQuery, state: FSMContext):
    message, cha_id = get_chat_context(callback)
    await callback.answer(Messages.Wait)
    await message.edit_text(Messages.Wait)
    # Save in DB
    phone_number = (await state.get_data()).get("number")
    async with get_db() as session:
        await services.user.add_identifier(session, cha_id, phone_number)
    # Send login code
    code = await services.whatsapp.login_code(phone_number)
    await message.edit_text(Messages.LoginCode.format(code=code))


# =============================================
# Select Contact's For Send Message
# =============================================
@DP.callback_query(
    states.SendMessage.SELECT, F.data.startswith(ui.CallbackData.CONTACTS_SELECT)
)
async def select_contact(callback: CallbackQuery, state: FSMContext):
    data: states.DataSendMessage = (await state.get_data()).get("data")
    selected = callback.data.split(";")[1]
    if selected in data.selected_contacts:
        data.selected_contacts.remove(selected)
    else:
        data.selected_contacts.append(selected)

    await state.update_data({"data": data})

    await callback.answer(Messages.Wait)
    await select_contecs(update=callable, state_data=data)


@DP.callback_query(
    states.SendMessage.SELECT, F.data.startswith(ui.CallbackData.CONTACTS_SELECT_ALL)
)
async def select_contact_all(callback: CallbackQuery, state: FSMContext):
    data: states.DataSendMessage = (await state.get_data()).get("data")
    data.select_all = not data.select_all
    await state.update_data({"data": data})

    await callback.answer(Messages.Wait)
    await select_contecs(update=callable, state_data=data)



@DP.callback_query(
    states.SendMessage.SELECT, F.data.startswith(ui.CallbackData.CONTACTS_PAGE)
)
async def change_page(callback: CallbackQuery, state: FSMContext):
    data: states.DataSendMessage = (await state.get_data()).get("data")
    data.page = int(callback.data.split(";")[1])
    await state.update_data({"data": data})
    
    await callback.answer(Messages.Wait)
    await select_contecs(update=callable, state_data=data)

    
# =============================================
# Start Resive Message
# =============================================
@DP.callback_query(
    states.SendMessage.SELECT, F.data.startswith(ui.CallbackData.CONFIRM)
)
async def resive_messages(callback: CallbackQuery, state: FSMContext):
    await callback.answer(Messages.Wait)
    await state.set_state(states.SendMessage.RESIVE)
    message, _ = get_chat_context(callback)
    await message.edit_text(Messages.Reseving_Message)
    await message.edit_reply_markup(reply_markup=ui.cancel())


# =============================================
# show interval send message
# =============================================
@DP.callback_query(
    states.SendMessage.RESIVE, F.data.startswith(ui.CallbackData.CONFIRM)
)
async def show_intervals(callback: CallbackQuery, state: FSMContext):
    message, _ = get_chat_context(callback)
    await callback.answer(Messages.Wait)

    await state.set_state(states.SendMessage.SELECT_INTERVAL)
    await message.edit_text(Messages.Select_Interval)
    await message.edit_reply_markup(reply_markup=ui.interval_select())


# =============================================
# Select interval send message
# =============================================
@DP.callback_query(
    states.SendMessage.SELECT_INTERVAL,
    F.data.startswith(ui.CallbackData.INTERVAL_SELECT),
)
async def select_interval(callback: CallbackQuery, state: FSMContext):
    message, _ = get_chat_context(callback)
    await callback.answer(Messages.Wait)

    data: states.DataSendMessage = (await state.get_data()).get("data")
    selected = callback.data.split(";")[1]
    __map = {
        "0": states.IntervalSendMessageMode.VEREY_FAST,
        "1": states.IntervalSendMessageMode.FAST,
        "2": states.IntervalSendMessageMode.NORMAL,
        "3": states.IntervalSendMessageMode.SLOW,
    }
    data.interval_mode = __map.get(str(selected), 3)
    await state.update_data({"data": data})
    await state.set_state(states.SendMessage.SEND)

    await message.edit_text(Messages.Confirm_Start_Send)
    await message.edit_reply_markup(reply_markup=ui.confirm())


# =============================================
# Start Send Message
# =============================================
@DP.callback_query(states.SendMessage.SEND, F.data.startswith(ui.CallbackData.CONFIRM))
async def start_send_message(callback: CallbackQuery, state: FSMContext):
    await callback.answer(Messages.Wait)
    return await send_message_prosess(callback, state)
