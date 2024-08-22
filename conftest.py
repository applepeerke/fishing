import json
import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.main import app
from src.utils.db.db import Base, get_async_engine

load_dotenv()
os.environ['DATABASE_URI'] = os.getenv('DATABASE_URI_TEST')
async_engine = get_async_engine()


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
            base_url=f"http://{os.getenv('API_V1_PREFIX')}",
            transport=ASGITransport(app=app)
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_session() -> AsyncSession:
    session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with session() as s:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield s

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()


@pytest.fixture(scope="function")
def test_data_fishingwater() -> dict:
    return _get_json('fishingwater')


@pytest.fixture(scope="function")
def test_data_user() -> dict:
    return _get_json('user')


@pytest.fixture(scope="function")
def test_data_systemvalue() -> dict:
    return _get_json('systemvalue')


@pytest.fixture(scope="function")
def test_data_login() -> dict:
    return _get_json('login')


@pytest.fixture(scope="function")
def test_data_login_tdd() -> dict:
    return _get_json('login_tdd')


def _get_json(domain) -> dict:
    """ Retrieve JSON from fishing/tests/data/{domain}.json"""
    path = os.getenv('PYTEST_CURRENT_TEST')
    path = os.path.join(*os.path.split(path)[:-1], "data", f"{domain}.json")

    if not os.path.exists(path):
        path = os.path.join("data", f"{domain}.json")

    with open(path, "r") as file:
        data = json.loads(file.read())

    return data
