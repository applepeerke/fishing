import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.entities.fish.models import Fish
from src.domains.entities.fish_species.models import FishSpecies
from src.utils.tests.constants import FISHSPECIES, CREATE, READ, UPDATE, DELETE
from src.utils.tests.crud_test import CrudTest

domain_url = 'fish'


@pytest.mark.asyncio
async def test_create(client: AsyncClient, db: AsyncSession, test_data_fish: dict):
    crud_test = CrudTest(client, db, test_data_fish, domain_url)
    # Create FishSpecies FK record and update the fixtures with the FK-id.
    await crud_test.update_fixture_fk(FishSpecies, FISHSPECIES, CREATE)
    await crud_test.create()


@pytest.mark.asyncio
async def test_read(client: AsyncClient, db: AsyncSession, test_data_fish: dict):
    crud_test = CrudTest(client, db, test_data_fish, domain_url, Fish)
    # Create FishSpecies FK record and update the fixtures with the FK-id.
    await crud_test.update_fixture_fk(FishSpecies, FISHSPECIES, READ)
    await crud_test.read()


@pytest.mark.asyncio
async def test_update(client: AsyncClient, db: AsyncSession, test_data_fish: dict):
    crud_test = CrudTest(client, db, test_data_fish, domain_url, Fish)
    # Create FishSpecies FK record and update the fixtures with the FK-id.
    await crud_test.update_fixture_fk(FishSpecies, FISHSPECIES, UPDATE)
    await crud_test.update()


@pytest.mark.asyncio
async def test_delete(client: AsyncClient, db: AsyncSession, test_data_fish: dict):
    crud_test = CrudTest(client, db, test_data_fish, domain_url, Fish)
    # Create FishSpecies FK record and update the fixtures with the FK-id.
    await crud_test.update_fixture_fk(FishSpecies, FISHSPECIES, DELETE)
    await crud_test.delete()
