import time
from asyncio import sleep
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import nio

from app.connctor import whatsapp as wa
from app.connctor.utils import MatrixUserManager, WhatsAppUser
from app.core.config import SETTINGS
from app.core.logging import logger

_last_sync = 0.0
_interval_sync = 120


async def sync_if_needed(connector: wa.WhatsAppConnected):

    global _last_sync
    if time.time() - _last_sync < _interval_sync:
        return

    await connector.sync()
    for s in ("group", "groups", "contacts"):
        await connector.send_text(await connector.bot_room(), f"!wa sync {s}")

    await connector.accept_invites()
    await connector.sync()
    _last_sync = time.time()


def filter_whatsapp_group(room: nio.MatrixRoom) -> bool:
    if not (room.name and room.display_name):
        return True
    if not ((room.room_type != "m.space") and (len(room.users) > 2)):
        return True
    return False


@asynccontextmanager
async def build_connector(
    identifier: str,
) -> AsyncGenerator[wa.WhatsAppConnected | None, None]:
    ws = wa.WhatsAppInit(
        username=WhatsAppUser.gen_username(identifier, SETTINGS.MATRIX_SERVER.DOMAIN),
        password=WhatsAppUser.gen_password(identifier, SETTINGS.MATRIX_SERVER.DOMAIN),
        homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
        identifier=identifier,
    )
    ws = await ws.login()
    client = await ws.connect()
    try:
        yield client
    finally:
        await ws.close()


async def login_code(identifier: str) -> str:
    admin_token = await MatrixUserManager.get_token(
        username=SETTINGS.MATRIX_SERVER.ADMIN_USERNAME,
        password=SETTINGS.MATRIX_SERVER.ADMIN_PASSWORD,
        homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
    )
    username = WhatsAppUser.gen_username(identifier, SETTINGS.MATRIX_SERVER.DOMAIN)
    password = WhatsAppUser.gen_password(identifier, SETTINGS.MATRIX_SERVER.DOMAIN)

    # if not (
    #     await MatrixUserManager.check_user_exists(
    #         homeserver=SETTINGS.MATRIX_SERVER.HOMESERVER,
    #         username=username,
    #         password=password,
    #     )
    # ):
    #     breakpoint()
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
    return await ws.login() # get code


async def get_groups(connector: wa.WhatsAppConnected):
    await sync_if_needed(connector)
    return await connector.get_dialogs(filter=filter_whatsapp_group)


async def send_text(
    connector: wa.WhatsAppConnected, room: nio.MatrixRoom, message: str
):
    return await connector.send_text(room.room_id, message)


async def send_media(
    connector: wa.WhatsAppConnected, room: nio.MatrixRoom, file: Path, caption: str
):
    media = await connector.send_media(room.room_id, file)
    text = None
    if caption:
        text = await send_text(connector, room, caption)

    return (media, text)
