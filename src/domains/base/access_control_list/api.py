from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.base.functions import get_delete_response
from src.db import crud
from src.db.db import get_db_session
from src.domains.scope.models import ScopeRead, Scope

scope = APIRouter()


@scope.post('/', response_model=ScopeRead)
async def create_scope(scope_create: ScopeRead, db: AsyncSession = Depends(get_db_session)):
    new_scope = Scope(entity=scope_create.entity, access=scope_create.access)
    return await crud.add(db, new_scope)


@scope.get('/', response_model=list[ScopeRead])
async def read_scopes(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_all(db, Scope, skip=skip, limit=limit)


@scope.get('/{id}', response_model=ScopeRead)
async def read_scope(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, Scope, id)


@scope.put('/{id}', response_model=ScopeRead)
async def update_scope(id: UUID, scope_update: ScopeRead, db: AsyncSession = Depends(get_db_session)):
    scope_update.id = id
    return await crud.upd(db, Scope, scope_update)


@scope.delete('/{id}')
async def delete_scope(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, Scope, id)
    return get_delete_response(success, Scope.__tablename__)

