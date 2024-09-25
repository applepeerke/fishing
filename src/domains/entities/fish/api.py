from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.base.functions import get_delete_response
from src.domains.entities.enums import FishStatus
from src.domains.entities.fish.models import Fish, FishRead, FishBase
from src.domains.entities.species.species import Species
from src.domains.login.token.functions import is_authorized

fish = APIRouter()


@fish.post('/', response_model=FishRead)
async def create_fish(
        fish_create: FishBase,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_create'])]
):
    new_fish = Fish(
        name=fish_create.name,
        species=fish_create.species,
        age=fish_create.age,
        length=fish_create.length,
        weight_in_g=fish_create.weight_in_g,
        subspecies=fish_create.subspecies,
        relative_density=fish_create.relative_density,
        active_at=fish_create.active_at,
        status=fish_create.status
    )
    return await crud.add(db, new_fish)


@fish.get('/', response_model=list[FishRead])
async def read_fishes(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, Fish, skip=skip, limit=limit)


@fish.get('/{id}', response_model=FishRead)
async def read_fish(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_read'])]
):
    return await crud.get_one(db, Fish, id)


@fish.put('/{id}', response_model=FishRead)
async def update_fish(
        id: UUID,
        fish_update: FishRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_update'])]
):
    fish_update.id = id
    return await crud.upd(db, Fish, fish_update)


@fish.delete('/{id}')
async def delete_fish(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_delete'])]
):
    success = await crud.delete(db, Fish, id)
    return get_delete_response(success, Fish.__tablename__)
