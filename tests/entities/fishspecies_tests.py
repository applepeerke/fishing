import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.entities.fishspecies.models import FishSpecies
from src.utils.tests.crud_test import CrudTest

domain_url = 'fishspecies'


@pytest.mark.asyncio
async def test_create(client: AsyncClient, db: AsyncSession, test_data_fishspecies: dict):
    crud_test = CrudTest(client, db, test_data_fishspecies, domain_url)
    await crud_test.create()


@pytest.mark.asyncio
async def test_read(client: AsyncClient, db: AsyncSession, test_data_fishspecies: dict):
    crud_test = CrudTest(client, db, test_data_fishspecies, domain_url, FishSpecies)
    await crud_test.read()


@pytest.mark.asyncio
async def test_update(client: AsyncClient, db: AsyncSession, test_data_fishspecies: dict):
    crud_test = CrudTest(client, db, test_data_fishspecies, domain_url, FishSpecies)
    await crud_test.update()


@pytest.mark.asyncio
async def test_delete(client: AsyncClient, db: AsyncSession, test_data_fishspecies: dict):
    crud_test = CrudTest(client, db, test_data_fishspecies, domain_url, FishSpecies)
    await crud_test.delete()
