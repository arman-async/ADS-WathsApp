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
    DEL_MESSAGE = "DEL_MESSAGE"
    CONTACTS_SELECT_RANDOM = "c_sr;"
    CONTACTS_SELECT_ALL = "c_sa:"
    CONTACTS_SELECT = "c_s;"
    CONTACTS_PAGE = "c_p;"
    INTERVAL_SELECT = "i_s;"
    REPET_SELECT = "r_s;"
    BANNER_ADD = "b_a;"
    BANNER_REMOVE = "b_r;"
    BANNER_SHOW_MESSAGES = "b_s;"
    BANNER_PANEL = "b_p;"


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
    selected: list[str] | None = None,
    selected_all: bool = False,
    selected_rand: bool = False,
    page: int = 0,
    page_size: int = 5,
) -> InlineKeyboardMarkup:
    selected = selected or []
    total_pages = math.ceil(len(items) / page_size) - 1

    page = max(page, 0)
    page = min(page, total_pages)

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
        InlineKeyboardButton(
            text=Buttons.Random,
            callback_data=CallbackData.CONTACTS_SELECT_RANDOM,
            style=ButtonStyle.PRIMARY if selected_rand else None,
        ),
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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=Buttons.Continue, callback_data=CallbackData.CONFIRM
                ),
            ],
            navigation,
            *contacts,
            page_up_down,
        ]
    )


def repet_select() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="تکرار غیرفعال",
                    callback_data=CallbackData.REPET_SELECT + "0",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="1 H",
                    callback_data=CallbackData.REPET_SELECT + "1",
                    style=ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    text="2 H",
                    callback_data=CallbackData.REPET_SELECT + "2",
                    style=ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    text="4 H",
                    callback_data=CallbackData.REPET_SELECT + "4",
                    style=ButtonStyle.DANGER,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="6 H",
                    callback_data=CallbackData.REPET_SELECT + "6",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    text="7 H",
                    callback_data=CallbackData.REPET_SELECT + "7",
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    text="8 H",
                    callback_data=CallbackData.REPET_SELECT + "8",
                    style=ButtonStyle.PRIMARY,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="12 H",
                    callback_data=CallbackData.REPET_SELECT + "12",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(
                    text="24 H",
                    callback_data=CallbackData.REPET_SELECT + "24",
                    style=ButtonStyle.SUCCESS,
                ),
            ],
        ]
    )


def banner_message_main_menu(banners: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    add = InlineKeyboardButton(
        text=Buttons.Add,
        callback_data=CallbackData.BANNER_ADD,
    )
    back = InlineKeyboardButton(
        text=Buttons.Back,
        callback_data=CallbackData.DEL_MESSAGE,
    )
    banners_but = [
        [
            InlineKeyboardButton(
                text=b[1],
                callback_data=CallbackData.BANNER_PANEL + str(b[0]),
            )
        ]
        for b in banners
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[*banners_but, [add, back]],
    )


def banner_message_panel(banner_id: int) -> InlineKeyboardMarkup:
    back = InlineKeyboardButton(
        text=Buttons.Back,
        callback_data=CallbackData.DEL_MESSAGE,
    )
    delete = InlineKeyboardButton(
        text=Buttons.Delete,
        callback_data=CallbackData.BANNER_REMOVE + str(banner_id),
    )
    show_messages = InlineKeyboardButton(
        text=Buttons.Show,
        callback_data=CallbackData.BANNER_SHOW_MESSAGES + str(banner_id),
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [delete, show_messages],
            [back],
        ],
    )
