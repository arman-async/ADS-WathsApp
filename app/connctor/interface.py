from typing import Awaitable, Callable, Optional, Protocol

from . import schemas

MessageCallback = Callable[[schemas.OnMessage], Awaitable[None]]
Cursor = str | None


class LoggedOutConnector(Protocol):
    async def login(self, **credentials) -> "LoggedInConnector":
        """
        Authenticate and return a LoggedInConnector state.
        Credentials differ per provider (token, session, qr, etc).
        """
        ...


class LoggedInConnector(Protocol):

    # -------------------------------
    # Sending messages
    # -------------------------------
    async def send_text(
        self,
        chat_id: str,
        text: str,
    ) -> dict: ...

    async def send_image(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str] = None,
    ) -> dict: ...

    async def send_video(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str] = None,
    ) -> dict: ...

    async def send_voice(
        self,
        chat_id: str,
        file_path: str,
    ) -> dict: ...

    async def send_file(
        self,
        chat_id: str,
        file_path: str,
    ) -> dict: ...

    # -------------------------------
    # History (cursor-based)
    # -------------------------------
    async def get_history(
        self, chat_id: str, cursor: Cursor, limit: int
    ) -> tuple[list[dict], Cursor]:
        """
        Returns (messages, next_cursor)
        next_cursor=None means end of history.
        """
        ...

    # -----------------------------------
    # Mark as read
    # -----------------------------------
    async def mark_as_read(self, chat_id: str, message_id: str) -> bool:
        """
        Returns True if operation succeeded.
        """
        ...

    # -----------------------------------
    # Message status
    # -----------------------------------
    async def get_message_status(self, chat_id: str, message_id: str) -> dict:
        """
        Returns message state.
        Example:
        {
            "delivered": True,
            "read": True,
            "read_at": "...",
        }
        """
        ...

    # -------------------------------
    # Profile info
    # -------------------------------
    async def get_profile(self) -> schemas.Dialog: ...

    # -------------------------------
    # Contacts
    # -------------------------------
    async def get_dialogs(self) -> list[schemas.Dialog]: ...

    # -------------------------------
    # Create private chat
    # -------------------------------
    async def create_chat(self, user_id: str) -> schemas.Dialog:
        """
        Returns chat_id
        """
        ...

    # -------------------------------
    # Real-time all messages
    # -------------------------------
    async def on_message(self, callback: MessageCallback) -> None:
        """
        Execute callback(message) whenever a new message arrives.
        Must run forever or until logout.
        """
        ...
    
    # -------------------------------
    # Stop listening
    # -------------------------------
    async def stop_on_message(self) -> None: ...

    # -------------------------------
    # Logout = return to LoggedOut state
    # -------------------------------
    async def logout(self) -> LoggedOutConnector: ...
