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
from src.utils.tests.functions import get_json, get_fixture_path
from tests.tdd.tdd import get_tdd_test_scenarios

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
    return get_json('fishingwater')


@pytest.fixture(scope="function")
def test_data_user() -> dict:
    return get_json('user')


@pytest.fixture(scope="function")
def test_data_systemvalue() -> dict:
    return get_json('systemvalue')


@pytest.fixture(scope="function")
def test_data_login() -> dict:
    return get_json('login')


@pytest.fixture(scope="function")
def test_data_encrypt() -> dict:
    return get_json('encrypt')


@pytest.fixture(scope="function")
def test_tdd_scenarios_login() -> dict:
    """ Retrieve CSV from fishing/tests/tdd/{domain}.csv"""
    path = get_fixture_path('tdd', 'login', 'csv')
    return get_tdd_test_scenarios(path)
