from typing import Annotated

from fastapi import APIRouter, Depends, Security, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db import crud
from src.db.db import get_db_session
from src.domains.entities.fishspecies.models import FishSpecies, FishSpeciesModel
from src.domains.entities.fisherman.models import Fisherman
from src.domains.entities.fishingwater.models import FishingWater
from src.domains.login.token.functions import is_authorized

catch = APIRouter()


@catch.post('/')
async def catch_a_fish(
        fish: FishSpeciesModel,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_catch'])],
):
    # Validations
    # Fish must not have been hooked.
    if not fish.fisherman_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='The fish was not hooked by a fisherman.')

    # Fish must not been caught already
    fish_old = await crud.get_one(db, FishSpecies, fish.id)
    if fish_old.fisherman_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='The fish was caught already.')

    fish_fishingwater = await crud.get_one(db, FishingWater, fish.fishingwater_id)
    # Fish must swim in a fishingwater
    if not fish_fishingwater:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='The fish does not swim in a fishing water.')

    # Fisherman must belong to the fishingwater of the fish.
    if not any(fisherman.id == fish.fisherman_id for fisherman in fish_fishingwater.fishermen):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='The fisherman is not allowed to fish in the fishingwater.')

    # GO!
    # - Remove the fish from the fishing water
    remaining_fishes = [existing_fish for existing_fish in fish_fishingwater.fishes if fish.id != fish.id]
    if len(remaining_fishes) != len(fish_fishingwater.fishes) - 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail='The fish could not be removed from the fishing water.')
    fish_fishingwater.fishes = remaining_fishes
    # - Add the fish to the fisherman
    fisherman = await crud.get_one(db, Fisherman, fish.fisherman_id)
    fisherman.fishes.append(fish)
    # Add fisherman to fish (ToDo: needed?)
    # fish.fisherman_id = fisherman.id
    # Commit!
    await db.commit()
