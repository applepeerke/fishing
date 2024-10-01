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
        no_of_fishes='1000',
        no_of_fishermen='3',
        no_of_initial_catches='0'
):

    simulator = Simulation()
    if not no_of_fishing_waters.isnumeric():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of fishing waters must be an integer.')
    if not no_of_fishes.isnumeric():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of fishes must be an integer.')
    if not no_of_fishermen.isnumeric():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of fishermen must be an integer.')
    if not no_of_initial_catches.isnumeric():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, 'Number of initial catches must be an integer.')

    await populate_fishing_with_random_data(
        db, int(no_of_fishing_waters), int(no_of_fishes), int(no_of_fishermen), int(no_of_initial_catches))
    await simulator.run(db)
