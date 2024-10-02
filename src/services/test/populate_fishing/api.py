import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db import crud
from src.db.db import get_db_session
from src.domains.entities.enums import Day, WaterType, SpeciesEnum, FishStatus, Frequency
from src.domains.entities.fisherman.models import Fisherman
from src.domains.entities.fishingday.models import FishingDay
from src.domains.entities.fishingwater.models import FishingWater, FLOATING_WATER
from src.domains.entities.fishspecies.models import FishSpecies, FishSpeciesModel
from src.services.simulation.functions import create_a_random_fishspecies
from src.services.test.functions import login_with_fake_admin
from src.utils.functions import get_random_item

fake_fishing_data = APIRouter()

# Fishermen
fake_forenames = ['Piet', 'Jan', 'Klaas', 'Petra', 'Harrie', 'Agnes', 'Hans', 'Johan', 'Ans', 'John', 'Hilda']
fake_surnames = ['Paaltjens', 'Klaassen', 'Janssen', 'Huibrechts', 'Ketting', 'Winter', 'Roelofs', 'Mol',
                 'Bergmans', 'Voys', 'Pardon']

# Locations
fake_city_names = ['Leiden', 'Den Haag', 'Amsterdam', 'Rotterdam', 'Delft', 'Zoetermeer', 'Zoeterwoude', 'Warmond',
                   'Abcoude', 'Capelle', 'Bodegraven']
fake_direction = ['O', 'ZO', 'Z', 'ZW', 'W', 'NW', 'N', 'NO']


days = [FishingDay(name=Day.Sunday), FishingDay(name=Day.Monday), FishingDay(name=Day.Tuesday),
        FishingDay(name=Day.Wednesday), FishingDay(name=Day.Thursday), FishingDay(name=Day.Friday),
        FishingDay(name=Day.Saturday)]


@fake_fishing_data.post('/')
async def create_random_fishing_data(
        db: AsyncSession = Depends(get_db_session),
        no_of_fishes='200',
        no_of_fishingwaters='2',
        no_of_fishermen='10',
        no_of_catches='20'
):
    # Authorize user
    await login_with_fake_admin(db)
    # Populate fishing db with random data
    await populate_fishing_with_random_data(
        db, int(no_of_fishingwaters), int(no_of_fishes), int(no_of_fishermen), int(no_of_catches))


async def populate_fishing_with_random_data(db, no_of_fishingwaters, no_of_fishes, no_of_fishermen, no_of_catches=0):
    # Create random data
    all_fishes = await _create_random_fishes(db, no_of_fishes)
    all_fishingwaters = await _create_random_fishingwaters(db, no_of_fishingwaters, no_of_fishes)
    all_fishermen = await _create_fishermen(db, no_of_fishermen)
    if not all_fishes or not all_fishermen or not all_fishingwaters:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Random initial data could not be created.')
    # Create random relations
    await _create_random_fishing_relations(db, all_fishingwaters, all_fishermen, all_fishes)
    # Catch some fishes
    target_catch_count = min(no_of_catches, no_of_fishes)
    [await _catch_a_random_fish(db, all_fishes, all_fishermen) for _ in range(target_catch_count)]


async def _create_random_fishes(db, no_of_fishes: int) -> [FishSpecies]:
    [await crud.delete(db, FishSpecies, item.id) for item in await crud.get_all(db, FishSpecies)]
    [await crud.add(db, create_a_random_fishspecies()) for _ in range(int(no_of_fishes))]
    return await crud.get_all(db, FishSpecies)


async def _create_random_fishingwaters(db, no_of_fishingwaters: int, no_of_fishes: int) -> [FishingWater]:
    locations = list({
        _concat_random_items([fake_city_names, [e for e in WaterType], fake_direction])
        for _ in range(no_of_fishingwaters)})

    [await crud.delete(db, FishingWater, item.id) for item in await crud.get_all(db, FishingWater)]
    [await _add_fishing_water(db, location=locations[i], no_of_fishes=no_of_fishes) for i in range(no_of_fishingwaters)]
    return await crud.get_all(db, FishingWater)


async def _add_fishing_water(db, location, no_of_fishes: int):
    water_type = get_random_item([e for e in WaterType])
    if water_type in FLOATING_WATER:
        m3 = 0  # Endless water
        density = 0.2  # Density always > 0
        no_of_fishes = 0  # Endless fishes
    else:
        m3 = random.randint(1000, max(1001, int(no_of_fishes * 10)))
        density = no_of_fishes / m3
    await crud.add(db, FishingWater(
        location=location,
        water_type=water_type,
        fishes_count=no_of_fishes,
        density=density,
        m3=m3))


async def _create_fishermen(db, no_of_fishermen: int) -> [Fisherman]:
    fisherman_names = list(
        {_concat_random_items([fake_forenames, fake_surnames], separator=' ') for _ in range(no_of_fishermen)})

    [await crud.delete(db, Fisherman, item.id) for item in await crud.get_all(db, Fisherman)]
    [await crud.add(db, Fisherman(
        forename=fisherman_names[i].split()[0],
        surname=fisherman_names[i].split()[1],
        fish_species=get_random_item([e for e in SpeciesEnum]),
        frequency=get_random_item([e for e in Frequency]),
        fishing_session_duration=random.randint(3, 12),
        status=get_random_item([e for e in FishStatus])))
     for i in range(no_of_fishermen)]
    return await crud.get_all(db, Fisherman)


async def _catch_a_random_fish(db, all_fishes, all_fishermen):
    # Get a random swimming fish
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
    fish_species = FishSpeciesModel(
        species_name=fish.species_name,
        subspecies_name=fish.subspecies_name,
        active_at=fish.active_at,
        relative_density=fish.relative_density,
        status=fish.status,
        fisherman_id=fisherman.id,
        fishingwater_id=fish.fishingwater_id
    )
    await crud.upd(db, FishSpecies, fish_species)


async def _create_random_fishing_relations(db, all_fishingwaters, all_fishermen, all_fishes):
    fisherman_count = random.randint(1, len(all_fishermen)) if len(all_fishermen) > 1 else 1  # 1-all fishermen
    fisherman_random_index_set = _get_random_index_set(all_fishermen, fisherman_count)
    # Add random fishing days to fishermen
    [all_fishermen[i].fishing_days.append(d)
     for i in fisherman_random_index_set
     for d in _get_random_days()]
    # Select the fishermen
    s = 0
    # Mean density of fishes over all the waters.
    mean_density = sum(fw.density for fw in all_fishingwaters) / len(all_fishingwaters)
    # Process fishingwaters
    for fishingwater in all_fishingwaters:
        # Divide fishes over the waters depending on fish density of the water.
        fishes_per_water = int((len(all_fishes) / len(all_fishingwaters)) * (fishingwater.density / mean_density))
        # Add fishermen
        [fishingwater.fishermen.append(all_fishermen[i]) for i in fisherman_random_index_set]
        # Add fishes (unique)
        e = min(s + fishes_per_water, len(all_fishes))
        [fishingwater.fishes.append(fish) for fish in all_fishes[s:e]]
        s = e
    await db.commit()


def _get_random_index_set(items: list, random_subset_count: int) -> set:
    set_count = len(items)
    if set_count == 0:
        return set()
    if set_count == 1:
        return {0}

    index_set = set()
    count = 0
    while len(index_set) < random_subset_count and count < 1000:
        count += 1
        index_set.add(random.randint(0, set_count - 1))  # get an index
    return index_set


def _concat_random_items(lists: list, separator='-') -> str:
    """ Concatenate random elements in 1-n lists """
    return separator.join([get_random_item(items) for items in lists])


def _get_random_days() -> [Day]:
    result = set()
    days_count = random.randint(0, 6)
    count = 0
    while len(result) < days_count and count < 1000:
        count += 1
        i = random.randint(0, 6)
        result.add(days[i])
    return list(result)
