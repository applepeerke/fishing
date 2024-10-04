from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.db import get_db_session
from src.services.simulation.populate_fishing import populate_fishing_with_random_data
from src.services.test.functions import login_with_fake_admin

fake_fishing_data = APIRouter()


@fake_fishing_data.post('/')
async def create_random_fishing_data(
        db: AsyncSession = Depends(get_db_session),
        no_of_fishing_waters='2',
        no_of_fishermen='10',
        no_of_fish_species='5',
        no_of_fishes='200',
        no_of_initial_catches='0'
):
    # Authorize user
    await login_with_fake_admin(db)

    # Populate fishing db with random data
    await populate_fishing_with_random_data(
        db,
        no_of_fishingwaters=int(no_of_fishing_waters),
        no_of_fishermen=int(no_of_fishermen),
        no_of_fish_species=int(no_of_fish_species),
        no_of_fishes=int(no_of_fishes),
        no_of_catches=int(no_of_initial_catches)
    )
