import time
from asyncio import sleep
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

import nio

from app.connctor import whatsapp as wa
from app.connctor.utils import MatrixUserManager, WhatsAppUser
from app.core.config import SETTINGS
from app.core.logging import logger

_last_sync_contacts = 0.0
_interval_sync_contacts = (3600 * 24) * 2


async def sync_contacts(connector: wa.WhatsAppConnected):
    global _last_sync_contacts
    if time.time() - _last_sync_contacts < _interval_sync_contacts:
        return
    await connector.sync()
    for s in ("group", "groups", "contacts"):
        await connector.send_text(await connector.bot_room(), f"!wa sync {s}")

    await connector.accept_invites()
    _last_sync_contacts = time.time()


_last_sync = 0.0
_interval_sync = 300 * 2


async def sync(connector: wa.WhatsAppConnected):
    global _last_sync
    if time.time() - _last_sync < _interval_sync:
        return

    await sync_contacts(connector)
    await connector.sync()
    _last_sync = time.time()


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


@dataclass
class ConnctorCached:
    lock: bool = False
    cleint: wa.WhatsAppConnected


_CACHE_CONNCTOR: dict[str, dict[int, ConnctorCached]] = {}


async def _get_connctor_in_cache(identifier: str) -> ConnctorCached:
    global _CACHE_CONNCTOR
    in_cache = _CACHE_CONNCTOR.get(identifier, dict())
    for index, connctor in in_cache.items():
        try:
            is_connected = await connctor.cleint.is_connected()
        except Exception as e:
            logger.error(f"Conctor Filed: {e}")
            del is_connected[index]
        if is_connected:
            connctor.lock = True
            return connctor


async def _free_connctor_in_cache(identifier: str, c_cache: ConnctorCached) -> None:
    global _CACHE_CONNCTOR
    last_index = max(_CACHE_CONNCTOR.get(identifier, dict()).keys())
    last_index += 1
    c_cache.lock = False
    _CACHE_CONNCTOR[identifier][last_index] = c_cache


async def _set_connctor_in_cache(
    identifier: str, connctor: wa.WhatsAppConnected
) -> None:
    global _CACHE_CONNCTOR
    last_index = max(_CACHE_CONNCTOR.get(identifier, dict()).keys())
    last_index += 1
    _CACHE_CONNCTOR[identifier][last_index] = ConnctorCached(lock=True, cleint=connctor)


class WhatsAppConnectorManager:
    def __init__(self):
        self._cache: dict[str, dict[int, ConnctorCached]] = {}

    def _get_next_index(self, identifier: str) -> int:
        indices = self._cache.get(identifier, {}).keys()
        return max(indices) + 1 if indices else 0

    async def get_connector(self, identifier: str) -> ConnctorCached | None:
        if identifier not in self._cache:
            return None

        for index, connector in self._cache[identifier].items():
            if connector.lock:
                continue
            try:
                connector = await connector.cleint.is_connected()
            except Exception as e:
                logger.error(f"Connector check failed: {e}")
                del self._cache[identifier][index]

            connector.lock = True
            return connector
        return None

    async def free_connector(self, identifier: str, connector: ConnctorCached) -> None:
        if identifier not in self._cache:
            self._cache[identifier] = {}

        index = self._get_next_index(identifier)
        connector.lock = False
        self._cache[identifier][index] = connector

    async def set_connector(
        self, identifier: str, client: wa.WhatsAppConnected
    ) -> None:
        if identifier not in self._cache:
            self._cache[identifier] = {}

        index = self._get_next_index(identifier)
        self._cache[identifier][index] = ConnctorCached(lock=True, cleint=client)


_WATSAPP_CONNECTOR_MANAGER = WhatsAppConnectorManager()


@asynccontextmanager
async def build_connector(
    identifier: str,
) -> AsyncGenerator[wa.WhatsAppConnected | None, None]:
    start_time = time.perf_counter()
    in_cache = await _WATSAPP_CONNECTOR_MANAGER.get_connector(identifier)

    if in_cache:
        duration = time.perf_counter() - start_time
        logger.debug(
            f"Connector retrieved from cache: {identifier} | duration={duration:.4f}s"
        )
        try:
            yield in_cache.client
        finally:
            await _WATSAPP_CONNECTOR_MANAGER.free_connector(identifier, in_cache)
        return

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
        duration = time.perf_counter() - start_time
        logger.info(
            f"Connector initialized successfully: {identifier} | duration={duration:.4f}s"
        )

        try:
            yield client
        finally:
            await _WATSAPP_CONNECTOR_MANAGER.set_connector(identifier, client)
    except Exception as e:
        logger.error(f"Connector initialization failed: {identifier} | error={e}")
        raise e


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
    media = await connector.send_media(room.room_id, file)
    text = None
    if caption:
        text = await send_text(connector, room, caption)

    return (media, text)
