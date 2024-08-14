import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncAttrs
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Needed here for alembic
load_dotenv()


class Base(AsyncAttrs, DeclarativeBase):
    pass


def get_async_engine():
    return create_async_engine(os.getenv("DATABASE_URI"), echo=True, future=True)


async def get_db_session() -> AsyncSession:
    # Create a configured "Session" class
    async_session = sessionmaker(bind=get_async_engine(), class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def init_models(test=False):
    async with get_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
