from sqlalchemy import ScalarResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Identifier, User

async def add_user(db: AsyncSession, user_id: str) -> None:
    if (await get_user(db, user_id)) is not None:
        return
    db.add(User(user_id=user_id))

async def get_user(db: AsyncSession, user_id: str) -> User | None:
    return await db.get(User, user_id)


async def get_identifiers(db: AsyncSession, user_id: str) -> ScalarResult[Identifier]:
    return await db.scalars(select(Identifier).where(Identifier.user_id == user_id))


async def get_identifier(db: AsyncSession, phone: str) -> Identifier | None:
    return await db.get(Identifier, phone)


async def add_identifier(db: AsyncSession, user_id: str, phone: str) -> None:
    # remove existing identifier
    await db.execute(delete(Identifier).where(Identifier.user_id == user_id))

    db.add(Identifier(phone=phone, user_id=user_id))
