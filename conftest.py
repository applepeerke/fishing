import csv
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
from src.utils.tests.constants import PAYLOAD, EXPECT, EXPECT_DB
from src.utils.tests.functions import add_to_nested_dict, create_nested_dict

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
def test_scenarios_login() -> dict:
    return _get_test_scenarios('login')


def _get_json(domain) -> dict:
    """ Retrieve JSON from fishing/tests/data/{domain}.json"""
    with open(_get_path(domain, 'json'), "r") as file:
        data = json.loads(file.read())
    return data


def _get_path(domain, ext) -> str:
    path = os.getenv('PYTEST_CURRENT_TEST')
    path = os.path.join(*os.path.split(path)[:-1], "data", f"{domain}.{ext}")

    if not os.path.exists(path):
        path = os.path.join("data", f"{domain}.{ext}")
    return path


def _get_test_scenarios(domain) -> dict:
    """
    Retrieve JSON from fishing/tests/data/{domain}.csv
    Example:
    ------------------------------------------------------------------------------------------------------------------
    0               1    2    3      4           5        6                   7     8    9         10    11    12
    Title	        TC  Pre  Entity	Endpoint	Expected Input	           Repeat	Exp. Exception Expected    Next
                        Sts                                                         HTTP           Status
    ------------------------------------------------------------------------------------------------------------------
    Registration	1   10	 login	register	fail	{"email": "d@s.com"}	0	422 Exists     *NC		     -
    Registration	2   20	 login	register	fail	{"email": "d@s.com"}	0	422 Exists	   *NC		     -
    Registration	3   NR	 login	register	success	{"email": "d@s.com"}	0	200	           10 Inactive Send otp
    ------------------------------------------------------------------------------------------------------------------
    """
    path = _get_path(domain, 'csv')
    if not os.path.isfile(path):
        return {}
    rows = get_csv_rows(path)

    d = {}
    for row in rows:
        # Payload fixture (maybe repeated)
        d1 = {}
        count = int(row[7]) + 1
        for i in range(count):
            breadcrumbs = _get_breadcrumbs(row, PAYLOAD, i)
            d0 = create_nested_dict(breadcrumbs, row[6])
            d1 = merge_dicts(d1, d0)

        # Expected response - model: User.UserStatus
        breadcrumbs = _get_breadcrumbs(row, EXPECT_DB)
        expected_response = {'status': int(row[2]) if row[10] == '*NC' else int(row[10])}
        d2 = create_nested_dict(breadcrumbs, expected_response)
        d1 = merge_dicts(d1, d2)
        # Expected response - message: Exception
        if row[9]:  # Exception
            breadcrumbs = _get_breadcrumbs(row, EXPECT)
            expected_response = {'detail':  row[9]}
            d2 = create_nested_dict(breadcrumbs, expected_response)
            d1 = merge_dicts(d1, d2)
        # Merge dicts
        d = merge_dicts(d, d1)
    return d


def _get_breadcrumbs(row, leaf, i=0) -> list:
    breadcrumbs = [f'{row[1].zfill(3)}|{row[2]}|{row[8]}']  # ID
    breadcrumbs.extend(row[3:6])
    suffix = '' if i == 0 else f'-{i}'
    breadcrumbs.append(f'{leaf}{suffix}')
    return breadcrumbs


def merge_dicts(d1, d2):
    for key, value in d2.items():
        if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
            merge_dicts(d1[key], value)
        else:
            d1[key] = value
    return d1


def get_csv_rows(path=None, skip_rows=1):
    rows = _try_csv_rows(path, ',')
    if not rows or len(rows[0]) == 1:
        rows = _try_csv_rows(path, ';')
    return rows[skip_rows:] if len(rows) > skip_rows else []


def _try_csv_rows(path, delimiter) -> list:
    with open(path, encoding='utf-8-sig', errors='replace') as csvFile:
        csv_reader = csv.reader(
            csvFile, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
        return [row for row in csv_reader if row[0]]
