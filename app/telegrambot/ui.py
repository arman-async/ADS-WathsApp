import math
from dataclasses import dataclass

from aiogram.enums.button_style import ButtonStyle
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.strings import Buttons
from app.models.contacts import Contact


@dataclass
class CallbackData:
    CONFIRM = "confirm"
    CANCEL = "cancel"
    CONTACTS_SELECT_ALL = "c_sa:"
    CONTACTS_SELECT = "c_s;"
    CONTACTS_PAGE = "c_p;"
    INTERVAL_SELECT = "i_s;"


def confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=Buttons.Continue, callback_data=CallbackData.CONFIRM
                ),
                InlineKeyboardButton(
                    text=Buttons.Cancel, callback_data=CallbackData.CANCEL
                ),
            ]
        ]
    )


def cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=Buttons.Cancel, callback_data=CallbackData.CANCEL
                ),
            ]
        ]
    )


def interval_select() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=Buttons.Vrey_Fast,
                    callback_data=CallbackData.INTERVAL_SELECT + "0",
                    style=ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    text=Buttons.Fast, callback_data=CallbackData.INTERVAL_SELECT + "1"
                ),
                InlineKeyboardButton(
                    text=Buttons.Normal,
                    callback_data=CallbackData.INTERVAL_SELECT + "2",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=Buttons.Safe,
                    callback_data=CallbackData.INTERVAL_SELECT + "3",
                    style=ButtonStyle.PRIMARY,
                ),
            ],
        ]
    )


def list_contacts(
    items: tuple[Contact, ...],
    selected: list[str] = [],
    selected_all: bool = False,
    page: int = 0,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    total_pages = math.ceil(len(items) / page_size) - 1
    page = max(0, min(page, total_pages))
    start = page * page_size
    end = start + page_size
    paginated_items = items[start:end]
    contacts = [
        [
            InlineKeyboardButton(
                text=item.name,
                callback_data=f"{CallbackData.CONTACTS_SELECT}{item.id}",
                style=ButtonStyle.SUCCESS
                if (item.id in selected and not selected_all)
                else None,
            )
        ]
        for item in paginated_items
    ]
    navigation = [
        InlineKeyboardButton(
            text=Buttons.Select_All,
            callback_data=CallbackData.CONTACTS_SELECT_ALL,
            style=ButtonStyle.PRIMARY if selected_all else None,
        ),
        InlineKeyboardButton(text=Buttons.Continue, callback_data=CallbackData.CONFIRM),
    ]
    page_up_down = [
        InlineKeyboardButton(
            text=Buttons.Previous,
            callback_data=f"{CallbackData.CONTACTS_PAGE}{page - 1}",
        ),
        InlineKeyboardButton(
            text=Buttons.Next,
            callback_data=f"{CallbackData.CONTACTS_PAGE}{page + 1}",
        ),
        
    ]
    return InlineKeyboardMarkup(inline_keyboard=[navigation, *contacts, page_up_down])
