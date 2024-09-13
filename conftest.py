import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.constants import PASSWORD, LOGIN, SCOPES
from src.db.db import get_async_engine
from src.domains.base.models import Base
from src.main import app
from src.utils.tests.functions import get_json, get_fixture_path
from tests.tdd.TestCase import TestCase
from tests.tdd.tdd_login import get_tdd_test_scenarios_login
from tests.tdd.tdd_scopes import get_tdd_test_scenarios_scopes

load_dotenv()
os.environ['DATABASE_URI'] = os.getenv('DATABASE_URI_TEST')
async_engine = get_async_engine()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
            base_url=f"http://{os.getenv('API_V1_PREFIX')}",
            transport=ASGITransport(app=app)
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncSession:
    session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with session() as s:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield s

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()

""" 
CRUD 
"""


@pytest.fixture(scope="function")
def test_data_acl() -> dict:
    return get_json('acl')


@pytest.fixture(scope="function")
def test_data_fishingwater() -> dict:
    return get_json('fishingwater')


@pytest.fixture(scope="function")
def test_data_role() -> dict:
    return get_json('role')


@pytest.fixture(scope="function")
def test_data_scope() -> dict:
    return get_json('scope')


@pytest.fixture(scope="function")
def test_data_user() -> dict:
    return get_json('user')


""" 
Auth 
"""


@pytest.fixture(scope="function")
def test_data_encrypt() -> dict:
    return get_json('encrypt')


@pytest.fixture(scope="function")
def test_data_login() -> dict:
    return get_json(LOGIN)


@pytest.fixture(scope="function")
def test_data_password() -> dict:
    return get_json(PASSWORD)


"""
TDD
"""


@pytest.fixture(scope="function")
def test_tdd_scenarios_login() -> dict:
    """ Retrieve CSV from fishing/tests/tdd/automatic_tests_{domain}.csv"""
    path = get_fixture_path(LOGIN, 'csv', automatic_tests=True)
    return get_tdd_test_scenarios_login(path)


@pytest.fixture(scope="function")
def test_tdd_scenarios_scopes() -> list:
    """ Retrieve CSV from fishing/tests/tdd/automatic_tests_{domain}.csv"""
    path = get_fixture_path(SCOPES, 'csv', automatic_tests=True)
    return get_tdd_test_scenarios_scopes(path)
