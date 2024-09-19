from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.base.functions import get_delete_response
from src.domains.entities.fishingwater.models import FishingWater, FishingWaterRead, FishingWaterCreate
from src.db import crud
from src.db.db import get_db_session
from src.domains.login.token.functions import is_authorized

fishingwater = APIRouter()


@fishingwater.post('/', response_model=FishingWaterRead)
async def create_fishing(
        fishingwater_create: FishingWaterCreate,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishing_create'])]
):
    new_fishing = FishingWater(
        type=fishingwater_create.type,
        location=fishingwater_create.location
    )
    return await crud.add(db, new_fishing)


@fishingwater.get('/', response_model=list[FishingWaterRead])
async def read_fishings(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishing_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, FishingWater, skip=skip, limit=limit)


@fishingwater.get('/{id}', response_model=FishingWaterRead)
async def read_fishing(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishing_read'])]
):
    return await crud.get_one(db, FishingWater, id)


@fishingwater.put('/{id}', response_model=FishingWaterRead)
async def update_fishing(
        id: UUID,
        fishing_update: FishingWaterRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishing_update'])]
):
    fishing_update.id = id
    return await crud.upd(db, FishingWater, fishing_update)


@fishingwater.delete('/{id}')
async def delete_fishing(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['fishing_delete'])]
):
    success = await crud.delete(db, FishingWater, id)
    return get_delete_response(success, FishingWater.__tablename__)
