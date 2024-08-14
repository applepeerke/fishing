import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.systemvalue.models import SystemValue
from src.utils.tests.crud_test import CrudTest

domain_url = 'systemvalue'


@pytest.mark.asyncio
async def test_create(async_client: AsyncClient, async_session: AsyncSession, test_data_systemvalue: dict):
    crud_test = CrudTest(async_client, async_session, test_data_systemvalue, domain_url)
    await crud_test.create()


@pytest.mark.asyncio
async def test_read(async_client: AsyncClient, async_session: AsyncSession, test_data_systemvalue: dict):
    crud_test = CrudTest(async_client, async_session, test_data_systemvalue, domain_url, SystemValue)
    await crud_test.read()


@pytest.mark.asyncio
async def test_update(async_client: AsyncClient, async_session: AsyncSession, test_data_systemvalue: dict):
    crud_test = CrudTest(async_client, async_session, test_data_systemvalue, domain_url, SystemValue)
    await crud_test.update()


@pytest.mark.asyncio
async def test_delete(async_client: AsyncClient, async_session: AsyncSession, test_data_systemvalue: dict):
    crud_test = CrudTest(async_client, async_session, test_data_systemvalue, domain_url, SystemValue)
    await crud_test.delete()
