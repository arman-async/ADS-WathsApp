import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.models import Base, Identifier, User
from app.db.session import engine, get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.mark.asyncio
async def test_create_user():
    async with get_db() as session:
        session.add(User(user_id="user1"))

    async with get_db() as session:
        user = await session.get(User, "user1")
        assert user is not None
        assert user.user_id == "user1"


@pytest.mark.asyncio
async def test_add_identifiers():
    user_id = "user-multi"
    async with get_db() as session:
        session.add(User(user_id=user_id))
        session.add(Identifier(phone="+999", user_id=user_id))
        session.add(Identifier(phone="+888", user_id=user_id))

    async with get_db() as session:
        stmt = (
            select(User)
            .options(joinedload(User.identifiers))
            .where(User.user_id == user_id)
        )
        user = (await session.execute(stmt)).unique().scalar_one()
        assert len(user.identifiers) == 2


@pytest.mark.asyncio
async def test_relationship_query():
    async with get_db() as session:
        stmt = (
            select(Identifier)
            .options(joinedload(Identifier.user))
            .where(Identifier.phone == "+999")
        )
        ident = (await session.execute(stmt)).scalar_one()
        assert ident.user.user_id == "user-multi"


