from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import services
from app.core import strings
from app.core.logging import logger
from app.db.session import get_db
from app.telegrambot import ui

from . import states
from .client import DP
from .common import (
    require_login,
    require_user,
)
from .utils import extract_file_id, get_chat_context


@DP.message(Command("banner"))
@require_user
async def banner_menu(message: Message):
    
    async with get_db() as session:
        banners_in_db = await services.banner.get_banners(session, message.chat.id)
    if banners_in_db:
        banners = [(b.id, b.name) for b in banners_in_db]
    else:
        banners = []

    await message.reply(
        text="بنرهای شما",
        reply_markup=ui.banner_message_main_menu(banners=banners),
    )


@DP.callback_query(F.data.startswith(ui.CallbackData.BANNER_PANEL))
async def banner_message_panel(query: CallbackQuery):
    await query.answer(strings.Messages.Wait)
    message, _ = get_chat_context(query)
    banner_id = int(query.data.split(";")[1])
    async with get_db() as session:
        banner = await services.banner.get_banner(session, banner_id)
    if not banner:
        message.edit_text("بنر وجود ندارد")
        return
    await message.edit_text("مدیریت بنر")
    await message.edit_reply_markup(reply_markup=ui.banner_message_panel(banner_id))


@DP.callback_query(F.data.startswith(ui.CallbackData.BANNER_SHOW_MESSAGES))
async def show_banner_messages(query: CallbackQuery):
    await query.answer(strings.Messages.Wait)
    message, chat_id = get_chat_context(query)
    banner_id = int(query.data.split(";")[1])
    async with get_db() as session:
        banner = await services.banner.get_banner(session, banner_id)
    if not banner:
        message.edit_text("بنر وجود ندارد")
        return
    message_ids: list[int] = [int(i) for i in banner.messages.split(",")]
    if not message_ids:
        message.edit_text("بنر خالی است")
        return
    for msg_id in message_ids:
        try:
            await message.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=msg_id,
            )
        except Exception as e:
            logger.error(f"Failed to forward message: {e}")
            continue


@DP.callback_query(F.data.startswith(ui.CallbackData.BANNER_REMOVE))
async def delete_banner(query: CallbackQuery):
    await query.answer(strings.Messages.Wait)
    message, _ = get_chat_context(query)
    banner_id = int(query.data.split(";")[1])
    async with get_db() as session:
        await services.banner.delete_banner(session, banner_id)
    await message.edit_text("بنر حذف شد")


@DP.callback_query(F.data.startswith(ui.CallbackData.BANNER_ADD))
async def add_banner(query: CallbackQuery, state: FSMContext):
    await query.answer(strings.Messages.Wait)
    message, _ = get_chat_context(query)
    await state.set_state(states.AddBannerMessaeg.ENTER_NAME)
    await state.update_data({"q_message": message})
    await message.edit_text("نام یک نام برای بنر وارد کنید :")


@DP.message(F.text, states.AddBannerMessaeg.ENTER_NAME)
async def add_banner_name(message: Message, state: FSMContext):
    await state.update_data({"name": message.text})
    q_message = (await state.get_data()).get("q_message")
    await state.set_state(states.AddBannerMessaeg.RESIVE_MESSAGES)
    await q_message.edit_text(
        f"ایجاد بنر جدید\n\nنام بنر: {message.text}\n\nپیام ها بنر را ارسال کنید"
    )
    await message.delete()


@DP.message(states.AddBannerMessaeg.RESIVE_MESSAGES)
async def resive_banner_messages(message: Message, state: FSMContext):
    messages: list[Message] = (await state.get_data()).get("messages", [])
    if (not extract_file_id(message)) and (not message.text):
        logger.info(f"Drapped message: {message.message_id}")
        await message.delete()
        return

    messages.append(message)
    await state.update_data({"messages": messages})
    logger.info(f"Saved message In Banner: {message.message_id}")
    await message.reply(strings.Messages.Resevied_Message, reply_markup=ui.confirm())


@DP.callback_query(
    states.AddBannerMessaeg.RESIVE_MESSAGES, F.data.startswith(ui.CallbackData.CONFIRM)
)
async def add_banner_message(callback: CallbackQuery, state: FSMContext):
    message, chat_id = get_chat_context(callback)
    await callback.answer(strings.Messages.Wait)
    
    messages: list[Message] = (await state.get_data()).get("messages", [])
    banner_name = (await state.get_data()).get("name")
    messages_id = ",".join([str(i.message_id) for i in messages])
    await state.clear()
    async with get_db() as session:
        try:
            await services.banner.add_banner(
                db=session, user_id=str(chat_id), name=banner_name, messages=messages_id
            )
        except Exception as e:
            logger.critical(f"Failed to add banner: {e}", stack_info=True)
            await message.edit_text("خطا در اضافه کردن بنر")
        else:
            await message.edit_text("بنر با موفقیت اضافه شد" "\n\n /banner")
