from dataclasses import dataclass
from pathlib import Path

from yaml import safe_load  # type: ignore

from app.core.config import SETTINGS
from app.core.logging import logger

logger.info("Initializing strings loading process")

STRINGS_PATH = Path(SETTINGS.TELEGRAM_BOT.STRING_FILE)


def strings_load(yam_file: Path = STRINGS_PATH) -> dict[str, str]:
    data = {}
    try:
        with open(yam_file, "r", encoding="utf-8") as f:
            data = safe_load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load strings from {yam_file}: {e}")
        return {}


def string_get(key: str, yam_file: Path = STRINGS_PATH) -> str | None:
    all_strings = strings_load(yam_file)
    value = all_strings.get(key)
    if value is None:
        logger.warning(f"String key '{key}' not found in {yam_file}")
    return value


logger.info("Loading message definitions")


@dataclass
class Messages:
    Help: str = string_get("msg_help")
    Home: str = string_get("msg_home")
    Wait: str = string_get("msg_wait")
    Error: str = string_get("msg_error")
    SUCCESS: str = string_get("msg_sucss")
    Support: str = string_get("msg_support")
    Commands: str = string_get("msg_commands")
    Canceled: str = string_get("msg_canceled")
    Connected: str = string_get("msg_connected")
    LoginCode: str = string_get("msg_login_code")
    First_Start: str = string_get("msg_first_start")
    First_Login: str = string_get("msg_first_login")
    Error_Retry: str = string_get("msg_error_retry")
    Disconnected: str = string_get("msg_disconnected")
    Send_Prosess: str = string_get("msg_send_prosess")
    Select_Contact: str = string_get("msg_select_contact")
    Select_Interval: str = string_get("msg_select_interval")
    Reseving_Message: str = string_get("msg_reseving_message")
    Resevied_Message: str = string_get("msg_resevied_message")
    Send_Prosess_End: str = string_get("msg_send_prosess_end")
    Enter_Phonenumber: str = string_get("msg_enter_phonenumber")
    Confirm_or_Cancel: str = string_get("msg_confirm_or_cancel")
    Confirm_Start_Send: str = string_get("msg_confirm_start_send")

logger.info("Loading button definitions")


@dataclass
class Buttons:
    Fast: str = string_get("but_fast")
    Safe: str = string_get("but_safe")
    Cancel: str = string_get("but_cancel")
    Normal: str = string_get("but_normal")
    Continue: str = string_get("but_continue")
    Vrey_Fast: str = string_get("but_vrey_fast")
    Select_All: str = string_get("but_select_all")
