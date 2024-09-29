from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.base.functions import get_delete_response
from src.domains.entities.fishingday.models import FishingDay, FishingDayRead, FishingDayBase
from src.domains.login.token.functions import is_authorized

fishingday = APIRouter()


@fishingday.post('/', response_model=FishingDayRead)
async def create_fishingday(
        fishingday_create: FishingDayBase,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishingday_create'])]
):
    new_fishing = FishingDay(
        name=fishingday_create.name
    )
    return await crud.add(db, new_fishing)


@fishingday.get('/', response_model=list[FishingDayRead])
async def read_fishingdays(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishingday_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, FishingDay, skip=skip, limit=limit)


@fishingday.get('/{id}', response_model=FishingDayRead)
async def read_fishingday(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishingday_read'])]
):
    return await crud.get_one(db, FishingDay, id)


@fishingday.put('/{id}', response_model=FishingDayRead)
async def update_fishingday(
        id: UUID,
        fishingday_update: FishingDayRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishingday_update'])]
):
    fishingday_update.id = id
    return await crud.upd(db, FishingDay, fishingday_update)


@fishingday.delete('/{id}')
async def delete_fishingday(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishingday_delete'])]
):
    success = await crud.delete(db, FishingDay, id)
    return get_delete_response(success, FishingDay.__tablename__)
