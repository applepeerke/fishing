import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.fishing.models import Fishing
from src.utils.tests.crud_test import CrudTest

domain_url = 'fishing'


@pytest.mark.asyncio
async def test_create(async_client: AsyncClient, async_session: AsyncSession, test_data_fishing: dict):
    crud_test = CrudTest(async_client, async_session, test_data_fishing, domain_url)
    await crud_test.create()


@pytest.mark.asyncio
async def test_read(async_client: AsyncClient, async_session: AsyncSession, test_data_fishing: dict):
    crud_test = CrudTest(async_client, async_session, test_data_fishing, domain_url, Fishing)
    await crud_test.read()


@pytest.mark.asyncio
async def test_update(async_client: AsyncClient, async_session: AsyncSession, test_data_fishing: dict):
    crud_test = CrudTest(async_client, async_session, test_data_fishing, domain_url, Fishing)
    await crud_test.update()


@pytest.mark.asyncio
async def test_delete(async_client: AsyncClient, async_session: AsyncSession, test_data_fishing: dict):
    crud_test = CrudTest(async_client, async_session, test_data_fishing, domain_url, Fishing)
    await crud_test.delete()
