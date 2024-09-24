from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.base.functions import get_delete_response
from src.domains.entities.fisherman.models import Fisherman, FishermanRead, FishermanBase
from src.domains.login.token.functions import is_authorized

fisherman = APIRouter()


@fisherman.post('/', response_model=FishermanRead)
async def create_fisherman(
        fisherman_create: FishermanBase,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fisherman_create'])]
):
    new_fisherman = Fisherman(
        forename=fisherman_create.forename,
        surname=fisherman_create.surname
    )
    return await crud.add(db, new_fisherman)


@fisherman.get('/', response_model=list[FishermanRead])
async def read_fishermen(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fisherman_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, Fisherman, skip=skip, limit=limit)


@fisherman.get('/{id}', response_model=FishermanRead)
async def read_fisherman(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fisherman_read'])]
):
    return await crud.get_one(db, Fisherman, id)


@fisherman.put('/{id}', response_model=FishermanRead)
async def update_fisherman(
        id: UUID,
        fisherman_update: FishermanRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fisherman_update'])]
):
    fisherman_update.id = id
    return await crud.upd(db, Fisherman, fisherman_update)


@fisherman.delete('/{id}')
async def delete_fisherman(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fisherman_delete'])]
):
    success = await crud.delete(db, Fisherman, id)
    return get_delete_response(success, Fisherman.__tablename__)
