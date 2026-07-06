from typing import Tuple, Union

from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message


def get_chat_context(update: Union[Message, CallbackQuery]) -> Tuple[Message, int]:
    if isinstance(update, CallbackQuery):
        return update.message, update.from_user.id
    return update, update.chat.id


def extract_file_id(message: Message) -> str|None:
    match message.content_type:
        case ContentType.PHOTO:
            return message.photo[-1].file_id
        case ContentType.VIDEO:
            return message.video.file_id
        case ContentType.AUDIO:
            return message.audio.file_id
        case ContentType.VOICE:
            return message.voice.file_id
        case ContentType.DOCUMENT:
            return message.document.file_id
    return None

def get_extension_file(message: Message)-> str:
    match message.content_type:
        case ContentType.PHOTO:
            return ".jpg"
        case ContentType.VIDEO:
            return ".mp4"
        case ContentType.AUDIO:
            return ".mp3"
        case ContentType.VOICE:
            return ".ogg"
        case ContentType.DOCUMENT:
            return ".pdf"
    return ".ios"