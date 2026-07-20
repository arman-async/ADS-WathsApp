import time
from asyncio import sleep
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import nio
from async_lru import alru_cache

from app.connctor import whatsapp as wa
from app.connctor.utils import MatrixUserManager, WhatsAppUser
from app.core.config import SETTINGS
from app.core.logging import logger

INTERVAL_SYNC = 3600
INTERVAL_SYNC_CONTACTS = 3600 * 24


def filter_whatsapp_group(room: nio.MatrixRoom) -> bool:
    if not (room.name and room.display_name):
        return True
    if not ((room.room_type != "m.space") and (len(room.users) > 2)):
        return True
    return False


def filter_whatsapp_status_bradcast(room: nio.MatrixRoom) -> bool:
    title: str = room.name if room.name else room.display_name
    if title.lower() == "whatsapp status broadcast":
        return True
    return False


@alru_cache(ttl=INTERVAL_SYNC_CONTACTS)
async def sync_contacts(connector: wa.WhatsAppConnected):

    await connector.sync()
    for s in ("group", "groups", "contacts"):
        await connector.send_text(await connector.bot_room(), f"!wa sync {s}")

    await connector.accept_invites()


@alru_cache(ttl=INTERVAL_SYNC)
async def sync(connector: wa.WhatsAppConnected):
    await connector.sync()


# @alru_cache()
# async def builder_connctor(identifier: str) -> wa.WhatsAppConnected | None:
#     start_time = time.perf_counter()
#     logger.info(f"Building new WhatsApp connector: {identifier}")
#     ws = wa.WhatsAppInit(
#         username=WhatsAppUser.gen_username(identifier, SETTINGS.MATRIX_SERVER.DOMAIN),
#         password=WhatsAppUser.gen_password(identifier, SETTINGS.MATRIX_SERVER.DOMAIN),
#         homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
#         identifier=identifier,
#     )

#     try:
#         ws = await ws.login()
#         client = await ws.connect()
#     except Exception as e:
#         logger.error(f"Connector initialization failed: {identifier} | error={e}")
#         raise e
#     else:
#         duration = time.perf_counter() - start_time
#         logger.info(
#             f"Connector initialized successfully: {identifier} | duration={duration:.4f}s"
#         )
#         return client


_CONNECTOR_CACHE = {}
async def builder_connctor(identifier: str) -> wa.WhatsAppConnected | None:
    if identifier in _CONNECTOR_CACHE:
        return _CONNECTOR_CACHE[identifier]

    start_time = time.perf_counter()
    logger.info(f"Building new WhatsApp connector: {identifier}")
    
    ws = wa.WhatsAppInit(
        username=WhatsAppUser.gen_username(identifier, SETTINGS.MATRIX_SERVER.DOMAIN),
        password=WhatsAppUser.gen_password(identifier, SETTINGS.MATRIX_SERVER.DOMAIN),
        homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
        identifier=identifier,
    )

    try:
        ws = await ws.login()
        client = await ws.connect()
    except Exception as e:
        logger.error(f"Connector initialization failed: {identifier} | error={e}")
        raise e
    
    duration = time.perf_counter() - start_time
    logger.info(f"Connector initialized successfully: {identifier} | duration={duration:.4f}s")
    
    if client is not None:
        _CONNECTOR_CACHE[identifier] = client
        
    return client



@asynccontextmanager
async def get_connector(
    identifier: str,
) -> AsyncGenerator[wa.WhatsAppConnected | None, None]:
    yield await builder_connctor(identifier)


async def login_code(identifier: str) -> str:
    admin_token = await MatrixUserManager.get_token(
        username=SETTINGS.MATRIX_SERVER.ADMIN_USERNAME,
        password=SETTINGS.MATRIX_SERVER.ADMIN_PASSWORD,
        homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
    )
    username = WhatsAppUser.gen_username(identifier, SETTINGS.MATRIX_SERVER.DOMAIN)
    password = WhatsAppUser.gen_password(identifier, SETTINGS.MATRIX_SERVER.DOMAIN)

    await MatrixUserManager.user_create(
        admin_token=admin_token,
        username=username,
        password=password,
        homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
    )

    await sleep(1.2)

    ws = wa.WhatsAppInit(
        username=username,
        password=password,
        homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
        identifier=identifier,
    )

    ws = await ws.login()
    return await ws.login()  # get code


@alru_cache(ttl=3600)
async def get_groups(connector: wa.WhatsAppConnected):
    return await connector.get_dialogs(
        filter=lambda x: filter_whatsapp_group(x) or filter_whatsapp_status_bradcast(x)
    )


async def send_text(
    connector: wa.WhatsAppConnected, room: nio.MatrixRoom, message: str
):
    return await connector.send_text(room.room_id, message)


async def send_media(
    connector: wa.WhatsAppConnected, room: nio.MatrixRoom, file: Path, caption: str
):
    caption = caption or ""
    await connector.send_media(room.room_id, file, caption=caption)
    # text = None
    # if caption:
    #     text = await send_text(connector, room, caption)

