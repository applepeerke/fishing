from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.db import get_db_session
from src.services.simulation.simulation import Simulation
from src.services.test.functions import login_with_fake_admin
from src.services.test.populate_fishing.api import populate_fishing_with_random_data
from src.utils.client import get_async_client


simulation = APIRouter()


@simulation.post('/')
async def start_simulation(
        db: AsyncSession = Depends(get_db_session),
        no_of_fishing_waters='1',
        no_of_fishes='1000'
):
    # Authorize user
    response = await login_with_fake_admin(db)

    # Populate fishing db with random data
    from src.main import app
    client = get_async_client(app)

    await populate_fishing_with_random_data(
        db, client, response.headers, int(no_of_fishing_waters), int(no_of_fishes))

    simulator = Simulation()
    await simulator.run(db)
