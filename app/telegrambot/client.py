from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from app.core.config import SETTINGS
from app.core.logging import logger, setup_logger

from . import middleware

logger.info("Initializing bot session and dispatcher")
session = AiohttpSession(proxy=SETTINGS.TELEGRAM_BOT.PROXY)
BOT = Bot(
    token=SETTINGS.TELEGRAM_BOT.TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
DP = Dispatcher()

try:
    DP.callback_query.outer_middleware(
        middleware.OuterLogging(setup_logger("EventBot", "callback.log"))
    )
    DP.callback_query.middleware(
        middleware.InnerLogging(setup_logger("EventBot", "callback.log"))
    )

    DP.message.outer_middleware(
        middleware.OuterLogging(setup_logger("EventBot", "msg.log"))
    )
    DP.message.middleware(middleware.InnerLogging(setup_logger("EventBot", "msg.log")))

    logger.info("Bot components and middlewares initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize middlewares: {e}")
