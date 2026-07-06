from dataclasses import dataclass


@dataclass
class Contact:
    id: str
    name: str
    number: str | None = None
