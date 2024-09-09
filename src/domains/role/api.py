from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.base.functions import get_delete_response
from src.db import crud
from src.db.db import get_db_session
from src.domains.role.models import RoleRead, Role

role = APIRouter()


@role.post('/', response_model=RoleRead)
async def create_role(role_create: RoleRead, db: AsyncSession = Depends(get_db_session)):
    new_role = Role(name=role_create.name)
    return await crud.add(db, new_role)


@role.get('/', response_model=list[RoleRead])
async def read_roles(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_all(db, Role, skip=skip, limit=limit)


@role.get('/{id}', response_model=RoleRead)
async def read_role(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, Role, id)


@role.put('/{id}', response_model=RoleRead)
async def update_role(id: UUID, role_update: RoleRead, db: AsyncSession = Depends(get_db_session)):
    role_update.id = id
    return await crud.upd(db, Role, role_update)


@role.delete('/{id}')
async def delete_role(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, Role, id)
    return get_delete_response(success, Role.__tablename__)

