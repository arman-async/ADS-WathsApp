from typing import NewType, Any

from pydantic import BaseModel

Total = NewType("Total", int)
RoomID = NewType("RoomID", str)


class Dialog(BaseModel):
    room_id: RoomID
    display_name: str | None
    avatar_url: str | None
    room : Any| None = None