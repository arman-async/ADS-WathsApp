from sqlalchemy import Sequence, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BannerMessages


async def get_banners(
    db: AsyncSession, user_id: str
) :
    banners_q = await db.scalars(
        select(BannerMessages).where(BannerMessages.user_id == user_id)
    )
    if banners_q is None:
        return None
    return banners_q.all()


async def get_banner(db: AsyncSession, banner_id: int):
    return await db.get(BannerMessages, banner_id)


async def delete_banner(db: AsyncSession, banner_id: str) -> None:
    banner = await db.get(BannerMessages, banner_id)
    if banner is None:
        return
    await db.execute(delete(BannerMessages).where(BannerMessages.id == banner_id))


async def add_banner(db: AsyncSession, user_id: str, name: str, messages: str) -> None:
    new_banner = BannerMessages(name=name, messages=messages, user_id=user_id)
    
    db.add(new_banner)
    
