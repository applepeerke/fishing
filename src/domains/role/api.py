from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.base.functions import get_delete_response
from src.db import crud
from src.db.db import get_db_session
from src.domains.role.models import RoleRead, Role
from src.domains.token.functions import is_authorized

role = APIRouter()


@role.post('/', response_model=RoleRead)
async def create_role(
        role_create: RoleRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['role_create'])]
):
    new_role = Role(name=role_create.name)
    return await crud.add(db, new_role)


@role.get('/', response_model=list[RoleRead])
async def read_roles(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['role_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, Role, skip=skip, limit=limit)


@role.get('/{id}', response_model=RoleRead)
async def read_role(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['role_read'])],
):
    return await crud.get_one(db, Role, id)


@role.put('/{id}', response_model=RoleRead)
async def update_role(
        id: UUID, role_update: RoleRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['role_update'])]
):
    role_update.id = id
    return await crud.upd(db, Role, role_update)


@role.delete('/{id}')
async def delete_role(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['role_delete'])]
):
    success = await crud.delete(db, Role, id)
    return get_delete_response(success, Role.__tablename__)
