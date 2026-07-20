import asyncio
import os
from pathlib import Path
from typing import Awaitable, Callable, Optional, Type, Union

import aiofiles.os
import magic
import nio
import numpy as np
from pydub import AudioSegment

from .schemas import Dialog, RoomID, Total


# ============================================================
# LoggedOutConnector
# ============================================================
class MatrixLoggedOut:
    def __init__(self, username: str, password: str, homeserver: str):
        self.username = username
        self.password = password
        self.homeserver = homeserver

    async def create_client(
        self,
    ) -> tuple[nio.AsyncClient, nio.LoginResponse | nio.LoginError]:
        client = nio.AsyncClient(self.homeserver, self.username)
        return client, await client.login(self.password)

    async def login(self) -> "MatrixLoggedIn":
        client, login_resp = await self.create_client()
        if login_resp and login_resp.device_id:
            return MatrixLoggedIn(client, self.username, self.password)
        else:
            raise Exception("Matrix login failed")


# ============================================================
# LoggedInConnector
# ============================================================
class MatrixLoggedIn:
    def __init__(self, client: nio.AsyncClient, username: str = None, password: str = None):
        self.client = client
        self._msgtype_mapper = {
            "text": "m.text",
            "image": "m.image",
            "video": "m.video",
            "audio": "m.audio",
            "file": "m.file",
            "sticker": "m.sticker",
            "location": "m.location",
        }
        self.username = username
        self.password = password

    def start_sync_forever(self):
        async def background_sync():
            await self.client.sync_forever(timeout=30000)

        asyncio.create_task(background_sync())

    async def sync(self):
        # TODO: implement cache here for optimization
        return await self.client.sync(full_state=True)

    # ----------------------------------------
    # Sending Text Message
    # ----------------------------------------
    async def send_text(
        self, room_id: RoomID, text: str, reply_to: Optional[str] = None
    ) -> nio.RoomSendResponse | nio.RoomSendError:
        return await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": text,
                "m.relates_to": {"m.in_reply_to": {"event_id": reply_to}},
            },
        )

    # --------------------------
    # Send image message
    # --------------------------
    async def send_image(
        self, room_id: RoomID, file: Path, reply_to: Optional[str] = None
    ):
        mime_type = magic.from_file(file, mime=True)
        if not mime_type.startswith("image"):
            raise Exception("File is not an image")
        return await self.send_media(room_id, file, reply_to)

    # --------------------------
    # Send video message
    # --------------------------
    async def send_video(
        self, room_id: RoomID, file: Path, reply_to: Optional[str] = None
    ):
        mime_type = magic.from_file(file, mime=True)
        if not mime_type.startswith("video"):
            raise Exception("File is not a video")
        return await self.send_media(room_id, file, reply_to)

    # --------------------------
    # Send audio message
    # --------------------------
    async def send_audio(
        self, room_id: RoomID, file: Path, reply_to: Optional[str] = None
    ):
        mime_type = magic.from_file(file, mime=True)
        if not mime_type.startswith("audio"):
            raise Exception("File is not an audio")
        return await self.send_media(room_id, file, reply_to)

    # --------------------------
    # Send file message
    # --------------------------
    async def send_file(
        self, room_id: RoomID, file: Path, reply_to: Optional[str] = None
    ):
        return await self.send_media(room_id, file, reply_to)

    # --------------------------
    # Send voice message
    # --------------------------
    async def send_voice(
        self, room_id: RoomID, file: Path, reply_to: Optional[str] = None
    ):
        mime_type = magic.from_file(file, mime=True)
        if not mime_type.startswith("audio"):
            raise Exception("File is not an audio")

        file_stat = await aiofiles.os.stat(file)

        # Upload first
        mxc_uri = await self._upload_media(file)

        # Duration (ms)
        audio = AudioSegment.from_file(file)
        duration_ms = len(audio)

        # Generate waveform
        def make_waveform(file: Path):
            audio = AudioSegment.from_file(file)
            raw = np.array(audio.get_array_of_samples(), dtype=float)

            if len(raw) < 100:
                raw = np.pad(raw, (0, 100 - len(raw)), mode="edge")

            normalized = (np.abs(raw) / np.max(np.abs(raw))) * 1024
            waveform = normalized.astype(int)[:: len(normalized) // 100][:100].tolist()

            if len(waveform) < 100:
                waveform = waveform + [waveform[-1]] * (100 - len(waveform))

            return waveform

        # Waveform
        waveform_list = make_waveform(file)

        # Final Matrix Voice Message content
        content = {
            "msgtype": "m.audio",
            "body": "Voice message",
            "m.relates_to": {"rel_type": "m.replace", "event_id": reply_to},
            "url": mxc_uri,
            "info": {
                "mimetype": mime_type,
                "size": file_stat.st_size,
                "duration": duration_ms,
            },
            # MSC1767
            "org.matrix.msc1767.text": "Voice message",
            "org.matrix.msc1767.file": {
                "url": mxc_uri,
                "name": os.path.basename(file),
                "mimetype": mime_type,
                "size": file_stat.st_size,
            },
            "org.matrix.msc1767.audio": {
                "duration": duration_ms,
                "waveform": waveform_list,
            },
            # MSC3245 (flag)
            "org.matrix.msc3245.voice": {},
        }

        # Send
        resp = await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=content,
        )

        return resp

    # ----------------------------------------
    # Sending Media
    # ----------------------------------------
    async def send_media(
        self,
        room_id: RoomID,
        file: Path,
        reply_to: Optional[str] = None,
        caption: str = "",
    ) -> nio.RoomSendResponse | nio.RoomSendError:

        mime_type = magic.from_file(file, mime=True)
        file_stat = await aiofiles.os.stat(file)
        mxc_uri = await self._upload_media(file)

        content = {
            "body": caption,
            "filename": os.path.basename(file),
            "m.relates_to": {"rel_type": "m.replace", "event_id": reply_to},
            "info": {
                "size": file_stat.st_size,
                "mimetype": mime_type,
                "thumbnail_info": None,
                "thumbnail_url": None,
            },
            "msgtype": self._msgtype_mapper.get(mime_type.split("/")[0], "m.file"),
            "url": mxc_uri,
        }
        resp = await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content=content,
        )
        return resp

    # ----------------------------------------
    # Uploading Media
    # ----------------------------------------
    async def _upload_media(self, file: Path) -> str:
        mime_type = magic.from_file(file, mime=True)
        file_stat = await aiofiles.os.stat(file)

        async with aiofiles.open(file, "r+b") as f:
            resp, _maybe_keys = await self.client.upload(
                f,
                content_type=mime_type,
                filename=os.path.basename(file),
                filesize=file_stat.st_size,
            )

        if isinstance(resp, nio.UploadResponse):
            return resp.content_uri
        raise Exception(
            f"Upload failed, {resp.transport_response.status_code}:"
            f"{resp.transport_response.text}"
        )

    # ----------------------------------------
    # Get All Dialogs
    # ----------------------------------------
    async def get_dialogs(
        self,
        offset: int = 0,
        limit: int = None,
        filter: Callable[[nio.MatrixRoom], bool] = None,
    ) -> tuple[list[Dialog], Total]:

        await self.sync()
        _room_ids = tuple(self.client.rooms.keys())
        room_ids = sorted(_room_ids)

        dialogs: list[Dialog] = []
        for room_id in room_ids:
            room = self.client.rooms.get(room_id)
            
            if filter:
                if filter(room):
                    continue

            dialogs.append(
                Dialog(
                    room_id=RoomID(room_id),
                    display_name=room.display_name,
                    avatar_url=room.room_avatar_url,
                    room=room,
                )
            )

        if offset > 0:
            dialogs = dialogs[offset:]

        if limit is not None:
            dialogs = dialogs[:limit]

        return dialogs, Total(len(dialogs))

    # ----------------------------------------
    # History (cursor-based)
    # ----------------------------------------
    async def get_history(
        self, room_id: RoomID, offset: str | None, limit: int
    ) -> tuple[
        list[
            nio.RoomMessageText
            | nio.RoomMessageFile
            | nio.RoomMessageImage
            | nio.RoomMessageAudio
            | nio.RoomMessageVideo
        ],
        str | None,
    ]:

        try:
            resp = await self.client.room_messages(
                room_id=room_id,
                start=offset,
                limit=limit,
                direction="b",
            )

            if isinstance(resp, nio.RoomMessagesError):
                raise Exception(f"Matrix error: {resp.message}")

            messages = []
            for event in resp.chunk:
                if isinstance(event, nio.RoomMessage):
                    messages.append(event)

            return messages, resp.end

        except Exception as e:
            print(f"Error getting history: {e}")
            return [], None

    # ----------------------------------------
    # Mark as read
    # ----------------------------------------
    async def mark_as_read(self, room_id: RoomID, message_id: str) -> bool:
        await self.client.room_read_markers(room_id, message_id, read_event=message_id)
        return True

    # ----------------------------------------
    # Create chat
    # ----------------------------------------
    async def create_chat(self, user_id: str) -> Dialog:
        resp = await self.client.room_create(
            invite=[user_id],
            is_direct=True,
        )
        return Dialog(room_id=resp.room_id, display_name="", avatar_url=None)

    # ----------------------------------------
    # Real-time messages
    # ----------------------------------------
    async def start_on_message(
        self,
        callback: Callable[[nio.MatrixRoom, nio.Event], Optional[Awaitable[None]]],
        filter: Union[Type[nio.Event], tuple[Type[nio.Event], None]] = (
            nio.RoomMessage
        ),
    ) -> None:
        self.client.add_event_callback(callback=callback, filter=filter)

    # ----------------------------------------
    # Logout
    # ----------------------------------------
    async def close(self) -> MatrixLoggedOut:
        await self.client.close()
        return MatrixLoggedOut(self.username,self.password,self.client.homeserver)

    # # ----------------------------------------
    # # Message status (Matrix doesn’t expose much)
    # # ----------------------------------------
    # async def get_message_status(self, room_id: RoomID, message_id: str) -> dict:
    #    pass
