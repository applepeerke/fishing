from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.base.functions import get_delete_response
from src.domains.entities.fish.models import Fish, FishReadModel, FishModel
from src.domains.login.token.functions import is_authorized

fish = APIRouter()


@fish.post('/', response_model=FishReadModel)
async def create_fish(
        fish_create: FishModel,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_create'])]
):
    new_fish = Fish(
        fishspecies_id=fish_create.fishspecies_id,
        status=fish_create.status,
        age=fish_create.age,
        length_cm=fish_create.length_cm,
        weight_g=fish_create.weight_g,
        caught_count=fish_create.caught_count,
    )
    return await crud.add(db, new_fish)


@fish.get('/', response_model=list[FishReadModel])
async def read_fishes(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, Fish, skip=skip, limit=limit)


@fish.get('/{id}', response_model=FishReadModel)
async def read_fish(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fish_read'])]
):
    return await crud.get_one(db, Fish, id)


@fish.put('/{id}', response_model=FishReadModel)
async def update_fish(
        id: UUID,
        fish_update: FishReadModel,
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
