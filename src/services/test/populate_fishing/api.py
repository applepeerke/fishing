import random

from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.db import crud
from src.db.db import get_db_session
from src.domains.entities.enums import Day
from src.domains.entities.fish.models import Fish, FishBase
from src.domains.entities.fisherman.models import Fisherman
from src.domains.entities.fishingdays.models import FishingDay
from src.domains.entities.fishingwater.models import FishingWater
from src.domains.login.token.models import Authentication
from src.services.test.functions import create_fake_authenticated_user, create_a_random_fish
from src.utils.client import get_async_client

fake_fishing_data = APIRouter()

fake_fishermen = [['Piet', 'Paaltjens', 'Carp', 'Weekly', 48, 'Sleeping'],
                  ['Jan', 'Klaassen', 'Roach', 'Daily', 4, 'Sleeping'],
                  ['Klaas', 'Janssen', 'Ale', 'Weekly', 6, 'Sleeping'],
                  ['Agnes', 'Huibrechts', 'Perch', 'Monthly', 8, 'Sleeping']]

fake_fishingwaters = [['Leiden ZW', 'Kanaal', 30],
                      ['Leiden O', 'Vliet', 40],
                      ['Voorschoten', 'Meer', 100],
                      ['Leiderdorp de Zijl', 'Rivier', 50]]


days = [FishingDay(name=Day.Sunday), FishingDay(name=Day.Monday), FishingDay(name=Day.Tuesday),
        FishingDay(name=Day.Wednesday), FishingDay(name=Day.Thursday), FishingDay(name=Day.Friday),
        FishingDay(name=Day.Saturday), ]


@fake_fishing_data.post('/')
async def create_random_fishing_data(
        response: Response,
        db: AsyncSession = Depends(get_db_session),
        no_of_fishes='100',
        no_of_catches='20',
        clear_fishing_data=True
):
    # Authorize user
    email = 'fakedummy@example.nl'
    password = 'FakeWelcome01!'
    role_name = 'fake_admin'
    authentication: Authentication = await create_fake_authenticated_user(
        db, email, password, [role_name], clear_fishing_data)
    response.headers.append(AUTHORIZATION, f'{authentication.token_type} {authentication.access_token}')
    # Populate fishing db with random data
    from src.main import app
    client = get_async_client(app)
    await populate_fishing_with_random_data(db, client, response.headers, no_of_fishes, no_of_catches)


async def populate_fishing_with_random_data(db, client, headers, no_of_fishes, no_of_catches):
    # Create the fake Roles with their ACLs and Scopes.
    all_fishes = await _create_random_fishes(db, no_of_fishes)
    all_fishingwaters = await _create_fishingwaters(db, fake_fishingwaters)
    all_fishermen = await _create_fishermen(db, fake_fishermen)
    # Relations
    await _create_random_fishing_relations(db, all_fishingwaters, all_fishermen, all_fishes)
    # Catch some fishes
    catches = min(int(no_of_catches), int(no_of_fishes))
    [await _catch_a_random_fish(client, all_fishes, all_fishermen, headers) for _ in range(catches)]


async def _create_random_fishes(db, no_of_fishes) -> [Fish]:
    [await crud.delete(db, Fish, item.id) for item in await crud.get_all(db, Fish)]
    [await crud.add(db, create_a_random_fish()) for _ in range(int(no_of_fishes))]
    return await crud.get_all(db, Fish)


async def _create_fishingwaters(db, items: list) -> [FishingWater]:
    [await crud.delete(db, FishingWater, item.id) for item in await crud.get_all(db, FishingWater)]
    [await crud.add(db, FishingWater(location=item[0], type=item[1], density=item[2]))
     for item in items]
    return await crud.get_all(db, FishingWater)


async def _create_fishermen(db, items: list) -> [Fisherman]:
    [await crud.delete(db, Fisherman, item.id) for item in await crud.get_all(db, Fisherman)]
    [await crud.add(db, Fisherman(
        forename=item[0],
        surname=item[1],
        fish_species=item[2],
        frequency=item[3],
        fishing_session_duration=item[4],
        status=item[5]))
     for item in items]
    return await crud.get_all(db, Fisherman)


async def _catch_a_random_fish(client: AsyncClient, all_fishes, all_fishermen, headers):
    # Get random swimming fish
    swimming_fishes = [fish for fish in all_fishes if not fish.fisherman_id]
    fish = swimming_fishes[random.randint(0, len(swimming_fishes) - 1)]
    # Get random fisherman belonging to the fishingwater of the fish
    fishermen_for_the_water = [
        fisherman for fisherman in all_fishermen
        for water in fisherman.fishingwaters
        if fish.fishingwater_id == water.id]
    fisherman = fishermen_for_the_water[random.randint(0, len(fishermen_for_the_water) - 1)]
    pydantic_fish = FishBase(
        species=fish.species,
        subspecies=fish.subspecies,
        name=fish.name,
        age=fish.age,
        length=fish.length,
        weight_in_g=fish.weight_in_g,
        active_at=fish.active_at,
        relative_density=fish.relative_density,
        status=fish.status,
        fisherman_id=fisherman.id,
        fishingwater_id=None
    )
    await client.post('/fish/catch/', json=pydantic_fish.json(), headers=headers)


async def _create_random_fishing_relations(db, all_fishingwaters, all_fishermen, all_fishes):
    fisherman_count = random.randint(1, len(all_fishermen) - 1)  # 1-all fishermen
    fisherman_random_index_set = _get_random_index_set(all_fishermen, fisherman_count)
    # Add random fishing days to fishermen
    [all_fishermen[i].fishing_days.append(d)
     for i in fisherman_random_index_set
     for d in _get_random_days()]
    # Select the fishermen
    s = 0
    # Process fishingwaters
    for fishingwater in all_fishingwaters:
        fishes_per_water = int(len(all_fishes) / len(all_fishingwaters))
        # Add fishermen
        [fishingwater.fishermen.append(all_fishermen[i]) for i in fisherman_random_index_set]
        # Add fishes (unique)
        e = min(s + fishes_per_water, len(all_fishes))
        [fishingwater.fishes.append(fish) for fish in all_fishes[s:e]]
        s = e
    await db.commit()


def _get_random_index_set(items: list, random_subset_count: int) -> set:
    set_count = len(items)
    if set_count < random_subset_count or set_count == 0:
        return set()
    index_set = set()
    while len(index_set) < random_subset_count:
        index_set.add(random.randint(1, set_count - 1))  # get an index
    return index_set


def _get_random_days() -> [Day]:
    result = set()
    days_count = random.randint(0, 6)
    count = 0
    while len(result) < days_count and count < 1000:
        count += 1
        i = random.randint(0, 6)
        result.add(days[i])
    return list(result)
