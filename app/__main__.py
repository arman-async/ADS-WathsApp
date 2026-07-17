import asyncio

from app.core.logging import logger
from app.db.session import init_db
from app.telegrambot.client import BOT, DP

logger.info("Loading handlers")
# ruff: noqa: F403, E402
from app.telegrambot.callback import *
from app.telegrambot.command import *
from app.telegrambot.messages import *

logger.info("Handlers loaded successfully")


async def main() -> None:
    logger.info("Initializing database")
    await init_db()
    logger.info("Database initialized successfully")

    logger.info("Starting bot polling")
    try:
        await DP.start_polling(BOT, polling_timeout=60, handle_signals=True)
    except Exception as e:
        logger.critical(f"Bot failed to start: {e}", exc_info=True)
    finally:
        logger.info("Bot stopped")


if __name__ == "__main__":
    logger.info("Application starting")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
