from abc import ABC
from dataclasses import dataclass
from os import getenv
from typing import Any, ClassVar, TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()


class BaseSetting(ABC, BaseModel):
    Prifex: ClassVar[str]


T = TypeVar("T", bound=BaseSetting)


def build_config(model: type[T], extra: dict[str, Any] | None = None) -> T:
    env_vars = {}

    for name, field in model.model_fields.items():
        # Using the field name in uppercase, combined with the prefix
        env_key = f"{model.Prifex}{name}"
        value = getenv(env_key)

        if value is not None:
            env_vars[name] = value
    env_vars |= extra or {}
    return model(**env_vars)


class TelegramBot(BaseSetting):
    model_config = ConfigDict(extra="forbid")
    Prifex: ClassVar[str] = "TBOT_"
    TOKEN: str
    
    # ADMINS: list[str]
    STRING_FILE: str
    PROXY: str | None = None
    


class DB(BaseSetting):
    model_config = ConfigDict(extra="forbid")
    Prifex: ClassVar[str] = "DB_"
    URL: str


class MatrixServer(BaseSetting):
    model_config = ConfigDict(extra="forbid")
    Prifex: ClassVar[str] = "MS_"
    HOMESERVER: str
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    DOMAIN: str


@dataclass(frozen=True)
class Settings:
    DB: DB
    TELEGRAM_BOT: TelegramBot
    MATRIX_SERVER: MatrixServer

    @staticmethod
    def from_env():
        return Settings(
            DB=build_config(DB),
            TELEGRAM_BOT=build_config(TelegramBot),
            MATRIX_SERVER=build_config(MatrixServer),
        )


SETTINGS = Settings.from_env()
