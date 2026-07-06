import asyncio
import re
import unicodedata
from typing import Union

import nio

from .matrix import MatrixLoggedIn, MatrixLoggedOut
from .schemas import Dialog, RoomID


class WhatsAppInit(MatrixLoggedOut):
    def __init__(self, username: str, password: str, homeserver: str, identifier: str):
        super().__init__(username, password, homeserver)
        self.identifier = identifier

    async def login(self) -> "WhatsAppDisConnected":
        client, resp = await self.create_client()
        if not isinstance(resp, nio.LoginResponse):
            raise Exception("Matrix login failed")

        if resp and resp.device_id:
            return WhatsAppDisConnected(client, self.identifier)
        else:
            raise Exception("Matrix login failed")


class WhatsApp(MatrixLoggedIn):
    def __init__(self, client: nio.AsyncClient, identifier: str):
        super().__init__(client)
        self.identifier = identifier
        self.domain = self.client.user.split(":")[-1]
        self._bot_room_id: RoomID | None = None

    def _found_bot_room(self) -> RoomID | None:
        for room_id, room in self.client.rooms.items():
            if f"@whatsappbot:{self.domain}" in room.users:
                if "WhatsApp bridge bot" == room.display_name:
                    return RoomID(room_id)
        return None

    async def _create_bot_room(self) -> RoomID:
        res = await self.client.room_create(
            is_direct=True,
            invite=[f"@whatsappbot:{self.domain}"],
        )
        return res.room_id

    async def bot_room(self) -> RoomID:
        # Check if bot room is already found
        if self._bot_room_id:
            return self._bot_room_id

        await self.sync()
        # Try to find bot room
        room_id = self._found_bot_room()
        if room_id:
            self._bot_room_id = room_id
            return room_id

        # Create bot room
        await self._create_bot_room()
        await asyncio.sleep(2)

        # Try to find bot room again
        return await self.bot_room()

    async def is_connected(self) -> bool:
        await self.sync()
        await self.send_text(await self.bot_room(), "list-logins")
        for _ in range(64):
            await asyncio.sleep(0.05)
            message, _ = await self.get_history(await self.bot_room(), None, 1)
            if not message:
                continue
            body = message[0].body
            text = unicodedata.normalize("NFKD", body)

            # Connected State
            pattern_connected = re.compile(r"`CONNECTED`")
            if pattern_connected.findall(text):
                return True

            # Bad Credentials (logout)
            pattern_bad_credentials = re.compile(r"`BAD_CREDENTIALS`")
            if pattern_bad_credentials.findall(text):
                await self.send_text(await self.bot_room(), f"logout {self.identifier}")
                return False

        return False


class WhatsAppDisConnected(WhatsApp):
    async def login(self) -> str | None:
        await self.send_text(await self.bot_room(), f"login phone {self.identifier}")
        for _ in range(86):
            await asyncio.sleep(0.05)
            message, _ = await self.get_history(await self.bot_room(), None, 1)
            body = message[0].body
            text = unicodedata.normalize("NFKD", body)
            pattern = re.compile(r".*-.*")
            if pattern.findall(text):
                return text
        return None

    async def connect(self) -> Union["WhatsAppConnected", None]:
        if await self.is_connected():
            return WhatsAppConnected(self.client, self.identifier)
        return None


class WhatsAppConnected(WhatsApp):
    def generate_user_id(self, identifier: str) -> str:
        return (
            f"@whatsapp_{identifier.replace('+', '')}:{self.client.user.split(':')[-1]}"
        )

    async def accept_invites(self):
        await self.sync()
        for room_id, room in self.client.invited_rooms.items():
            try:
                await self.client.join(room_id)
            except nio.RoomInviteError:
                continue

    async def start_chat(self, identifier: str) -> Dialog | None:
        user_id = self.generate_user_id(identifier)
        room_id = None

        await self.sync()
        for _room_id, room in self.client.rooms.items():
            for user in room.users.keys():
                if user == user_id:
                    room_id = RoomID(_room_id)
                    break

        if not room_id:
            resp = await self.client.room_create(
                is_direct=True,
                invite=[user_id],
                topic="WhatsApp private chat",
                preset=nio.RoomPreset.private_chat,
            )
            if isinstance(resp, nio.RoomCreateError):
                return None
            room_id = RoomID(resp.room_id)

        await asyncio.sleep(0.5)
        await self.accept_invites()
        await self.sync()
        room = self.client.rooms.get(room_id)
        if not room:
            return None
        return Dialog(
            room_id=room.room_id,
            display_name=room.name,
            avatar_url=room.avatar_url(user_id),
        )

    async def is_outgoing_event(self, event: nio.Event) -> bool:
        """Return True if the message was sent by this client/user."""
        return event.sender == self.client.user

    async def logout(self) -> "WhatsAppDisConnected":
        await self.send_text(
            await self.bot_room(), f"logout {self.identifier.replace('+', '')}"
        )
        return WhatsAppDisConnected(self.client, self.identifier)

    async def disconnect(self) -> "WhatsAppDisConnected":
        # await self.send_text(await self.bot_room(), "logout")
        return WhatsAppDisConnected(self.client, self.identifier)
