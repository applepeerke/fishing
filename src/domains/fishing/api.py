from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.fishing.models import Fishing, FishingRead, FishingCreate
from src.general.models import get_delete_response, StatusResponse
from src.utils.db import crud
from src.utils.db.db import get_db_session

fishing = APIRouter()


@fishing.post('/', response_model=FishingRead)
async def create_fishing(fishing_create: FishingCreate, db: AsyncSession = Depends(get_db_session)):
    new_fishing = Fishing(
        type=fishing_create.type,
        location=fishing_create.location
    )
    return await crud.add(db, new_fishing)


@fishing.get('/', response_model=list[FishingRead])
async def read_fishings(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_all(db, Fishing, skip=skip, limit=limit)


@fishing.get('/{id}', response_model=FishingRead)
async def read_fishing(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, Fishing, id)


@fishing.put('/{id}', response_model=FishingRead)
async def update_fishing(id: UUID, fishing_update: FishingCreate, db: AsyncSession = Depends(get_db_session)):
    return await crud.upd(db, Fishing, id, fishing_update)


@fishing.delete('/{id}', response_model=StatusResponse)
async def delete_fishing(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, Fishing, id)
    return get_delete_response(success, Fishing.__tablename__)

