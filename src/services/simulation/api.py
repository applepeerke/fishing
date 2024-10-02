from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db.db import get_db_session
from src.services.simulation.simulation import Simulation
from src.services.test.populate_fishing.api import populate_fishing_with_random_data

simulation = APIRouter()


@simulation.post('/')
async def start_simulation(
        db: AsyncSession = Depends(get_db_session),
        no_of_fishing_waters='2',
        no_of_fishes='100',
        no_of_fishermen='3',
        no_of_initial_catches='0',
        start_year='2025',
        no_of_fishing_days='365',
):

    simulator = Simulation()

    if not no_of_fishing_waters.isnumeric() or int(no_of_fishing_waters) == 0 or int(no_of_fishing_waters) > 100:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Fishing waters must be a valid integer.')
    if not no_of_fishes.isnumeric() or int(no_of_fishes) == 0 or int(no_of_fishes) > 1000000:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of fishes must be a valid integer.')
    if not no_of_fishermen.isnumeric() or int(no_of_fishermen) == 0 or int(no_of_fishermen) > 1000:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of fishermen must be a valid integer.')
    if not no_of_initial_catches.isnumeric() or int(no_of_initial_catches) > 1000:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of initial catches must be a valid integer.')
    if not start_year.isnumeric() or int(start_year) < 2000 or int(start_year) > 3000:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Start year must be between 2000 and 3000.')
    if not no_of_fishing_days.isnumeric() or int(no_of_fishing_days) == 0 or int(no_of_fishing_days) > 3650:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of fishing days must be a valid integer.')

    await populate_fishing_with_random_data(
        db, int(no_of_fishing_waters), int(no_of_fishes), int(no_of_fishermen), int(no_of_initial_catches))

    await simulator.run(db, int(start_year), int(no_of_fishing_days))
