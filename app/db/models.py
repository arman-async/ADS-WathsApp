from typing import List
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    identifiers: Mapped[List["Identifier"]] = relationship(back_populates="user")

class Identifier(Base):
    __tablename__ = "identifiers"
    
    phone: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    
    user: Mapped["User"] = relationship(back_populates="identifiers")