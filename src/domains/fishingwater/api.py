from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.fishingwater.models import FishingWater, FishingWaterRead, FishingWaterCreate
from src.general.models import get_delete_response
from src.utils.db import crud
from src.utils.db.db import get_db_session

fishingwater = APIRouter()


@fishingwater.post('/', response_model=FishingWaterRead)
async def create_fishing(fishingwater_create: FishingWaterCreate, db: AsyncSession = Depends(get_db_session)):
    new_fishing = FishingWater(
        type=fishingwater_create.type,
        location=fishingwater_create.location
    )
    return await crud.add(db, new_fishing)


@fishingwater.get('/', response_model=list[FishingWaterRead])
async def read_fishings(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_all(db, FishingWater, skip=skip, limit=limit)


@fishingwater.get('/{id}', response_model=FishingWaterRead)
async def read_fishing(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, FishingWater, id)


@fishingwater.put('/{id}', response_model=FishingWaterRead)
async def update_fishing(id: UUID, fishing_update: FishingWaterCreate, db: AsyncSession = Depends(get_db_session)):
    return await crud.upd(db, FishingWater, id, fishing_update)


@fishingwater.delete('/{id}')
async def delete_fishing(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, FishingWater, id)
    return get_delete_response(success, FishingWater.__tablename__)

