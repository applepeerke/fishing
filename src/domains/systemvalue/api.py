from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.systemvalue.models import SystemValue, SystemValueRead, SystemValueCreate
from src.general.models import get_delete_response, StatusResponse
from src.utils.db import crud
from src.utils.db.db import get_db_session

systemvalue = APIRouter()


@systemvalue.post('/', response_model=SystemValueRead)
async def create_systemvalue(systemvalue_create: SystemValueCreate, db: AsyncSession = Depends(get_db_session)):
    new_systemvalue = SystemValue(
        token_expiration_days=systemvalue_create.token_expiration_days,
        max_login_failures=systemvalue_create.max_login_failures,
        block_minutes=systemvalue_create.block_minutes
    )
    return await crud.add(db, new_systemvalue)


@systemvalue.get('/{id}', response_model=SystemValueRead)
async def read_systemvalue(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, SystemValue, id)


@systemvalue.put('/{id}', response_model=SystemValueRead)
async def update_systemvalue(id: UUID, systemvalue_update: SystemValueCreate,
                             db: AsyncSession = Depends(get_db_session)):
    return await crud.upd(db, SystemValue, id, systemvalue_update)


@systemvalue.delete('/{id}', response_model=StatusResponse)
async def delete_systemvalue(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, SystemValue, id)
    return get_delete_response(success, SystemValue.__tablename__)
