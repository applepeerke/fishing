from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.base.functions import get_delete_response
from src.domains.entities.fishspecies.models import FishSpecies, FishReadModel, FishSpeciesModel
from src.domains.login.token.functions import is_authorized

fish = APIRouter()


@fish.post('/', response_model=FishReadModel)
async def create_fish(
        fish_create: FishSpeciesModel,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_create'])]
):
    new_fish = FishSpecies(
        species_name=fish_create.species_name,
        subspecies_name=fish_create.subspecies_name,
        relative_density=fish_create.relative_density,
        active_at=fish_create.active_at,
        status=fish_create.status
    )
    return await crud.add(db, new_fish)


@fish.get('/', response_model=list[FishReadModel])
async def read_fishes(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, FishSpecies, skip=skip, limit=limit)


@fish.get('/{id}', response_model=FishReadModel)
async def read_fish(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_read'])]
):
    return await crud.get_one(db, FishSpecies, id)


@fish.put('/{id}', response_model=FishReadModel)
async def update_fish(
        id: UUID,
        fish_update: FishReadModel,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_update'])]
):
    fish_update.id = id
    return await crud.upd(db, FishSpecies, fish_update)


@fish.delete('/{id}')
async def delete_fish(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_delete'])]
):
    success = await crud.delete(db, FishSpecies, id)
    return get_delete_response(success, FishSpecies.__tablename__)
