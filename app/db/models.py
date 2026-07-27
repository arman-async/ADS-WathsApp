from sqlalchemy import TEXT, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    identifiers: Mapped[list["Identifier"]] = relationship(back_populates="user")

    banner_messages: Mapped[list["BannerMessages"]] = relationship(back_populates="user")

class Identifier(Base):
    __tablename__ = "identifiers"

    phone: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))

    user: Mapped["User"] = relationship(back_populates="identifiers")


class BannerMessages(Base):
    __tablename__ = "banner_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))

    messages: Mapped[str] = mapped_column(TEXT)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    
    user: Mapped["User"] = relationship(back_populates="banner_messages")
