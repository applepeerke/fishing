import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.user.models import User
from src.utils.tests.crud_test import CrudTest

domain_url = 'user'


@pytest.mark.asyncio
async def test_create(client: AsyncClient, db: AsyncSession, test_data_user: dict):
    crud_test = CrudTest(client, db, test_data_user, domain_url)
    await crud_test.create()


@pytest.mark.asyncio
async def test_read(client: AsyncClient, db: AsyncSession, test_data_user: dict):
    crud_test = CrudTest(client, db, test_data_user, domain_url, User)
    await crud_test.read()


@pytest.mark.asyncio
async def test_update(client: AsyncClient, db: AsyncSession, test_data_user: dict):
    crud_test = CrudTest(client, db, test_data_user, domain_url, User)
    await crud_test.update()


@pytest.mark.asyncio
async def test_delete(client: AsyncClient, db: AsyncSession, test_data_user: dict):
    crud_test = CrudTest(client, db, test_data_user, domain_url, User)
    await crud_test.delete()

