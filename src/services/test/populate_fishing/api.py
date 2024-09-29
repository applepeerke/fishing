import random

from fastapi import APIRouter, Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.db import crud
from src.db.db import get_db_session
from src.domains.entities.enums import Day
from src.domains.entities.fish.models import Fish, FishBase
from src.domains.entities.fisherman.models import Fisherman
from src.domains.entities.fishingday.models import FishingDay
from src.domains.entities.fishingwater.models import FishingWater
from src.services.test.functions import create_a_random_fish, login_with_fake_admin, get_random_item
from src.utils.client import get_async_client

fake_fishing_data = APIRouter()

fake_fishermen = [['Piet', 'Paaltjens', 'Carp', 'Weekly', 48, 'Sleeping'],
                  ['Jan', 'Klaassen', 'Roach', 'Weekly', 4, 'Sleeping'],
                  ['Klaas', 'Janssen', 'Ale', 'Weekly', 6, 'Sleeping'],
                  ['Agnes', 'Huibrechts', 'Perch', 'Monthly', 8, 'Sleeping']]

fake_fishingwaters = [['Leiden ZW', 'Kanaal', 0.30, 0],
                      ['Leiden O', 'Vliet', 0.40, 0],
                      ['Voorschoten', 'Meer', 1.00, 10000],
                      ['Leiderdorp de Zijl', 'Rivier', 0.50, 0]]


days = [FishingDay(name=Day.Sunday), FishingDay(name=Day.Monday), FishingDay(name=Day.Tuesday),
        FishingDay(name=Day.Wednesday), FishingDay(name=Day.Thursday), FishingDay(name=Day.Friday),
        FishingDay(name=Day.Saturday), ]


@fake_fishing_data.post('/')
async def create_random_fishing_data(
        response: Response,
        db: AsyncSession = Depends(get_db_session),
        no_of_fishes='100',
        no_of_fishingwaters='4',
        no_of_catches='20',
        clear_fake_db='true'
):
    # Authorize user
    clear_fake_db = False if str(clear_fake_db).lower() == 'false' else True
    await login_with_fake_admin(db=db, clear_fake_db=clear_fake_db)
    # Populate fishing db with random data
    from src.main import app
    client = get_async_client(app)
    await populate_fishing_with_random_data(
        db, client, response.headers, int(no_of_fishingwaters), int(no_of_fishes), int(no_of_catches))


async def populate_fishing_with_random_data(db, client, headers, no_of_fishingwaters, no_of_fishes, no_of_catches=0):
    # Create random data
    all_fishes = await _create_random_fishes(db, no_of_fishes)
    all_fishingwaters = await _create_random_fishingwaters(db, fake_fishingwaters, no_of_fishingwaters)
    all_fishermen = await _create_fishermen(db, fake_fishermen)
    # Create random relations
    await _create_random_fishing_relations(db, all_fishingwaters, all_fishermen, all_fishes)
    # Catch some fishes
    target_catch_count = min(no_of_catches, no_of_fishes)
    [await _catch_a_random_fish(client, all_fishes, all_fishermen, headers) for _ in range(target_catch_count)]


async def _create_random_fishes(db, no_of_fishes: int) -> [Fish]:
    [await crud.delete(db, Fish, item.id) for item in await crud.get_all(db, Fish)]
    [await crud.add(db, create_a_random_fish()) for _ in range(int(no_of_fishes))]
    return await crud.get_all(db, Fish)


async def _create_random_fishingwaters(db, items: list, no_of_fishingwaters: int) -> [FishingWater]:
    no_of_fishingwaters = min(len(items), no_of_fishingwaters)
    index_set = _get_random_index_set(items, no_of_fishingwaters)
    items = [items[i] for i in range(len(items)) if i in index_set]
    [await crud.delete(db, FishingWater, item.id) for item in await crud.get_all(db, FishingWater)]
    [await crud.add(db, FishingWater(location=item[0], water_type=item[1], density=item[2], m3=item[3]))
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
    fish = get_random_item(swimming_fishes)
    # Get random fisherman belonging to the fishingwater of the fish
    fishermen_for_the_water = [
        fisherman for fisherman in all_fishermen
        for water in fisherman.fishingwaters
        if fish.fishingwater_id == water.id]
    # No fishermen for the water
    if not fishermen_for_the_water:
        return
    fisherman = get_random_item(fishermen_for_the_water)
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
        fishingwater_id=fish.fishingwater_id
    )
    await client.post('/fish/catch/', json=pydantic_fish.json(), headers=headers)


async def _create_random_fishing_relations(db, all_fishingwaters, all_fishermen, all_fishes):
    fisherman_count = random.randint(1, len(all_fishermen))  # 1-all fishermen
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
    index_set = set()
    count = 0
    while len(index_set) < random_subset_count and count < 1000:
        count += 1
        index_set.add(random.randint(0, set_count - 1))  # get an index
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
