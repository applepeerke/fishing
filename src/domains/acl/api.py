from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.base.functions import get_delete_response
from src.db import crud
from src.db.db import get_db_session
from src.domains.acl.models import ACLRead, ACL

acl = APIRouter()


@acl.post('/', response_model=ACLRead)
async def create_acl(acl_create: ACLRead, db: AsyncSession = Depends(get_db_session)):
    new_acl = ACL(name=acl_create.name)
    return await crud.add(db, new_acl)


@acl.get('/', response_model=list[ACLRead])
async def read_acls(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_all(db, ACL, skip=skip, limit=limit)


@acl.get('/{id}', response_model=ACLRead)
async def read_acl(id: UUID, db: AsyncSession = Depends(get_db_session)):
    return await crud.get_one(db, ACL, id)


@acl.put('/{id}', response_model=ACLRead)
async def update_acl(id: UUID, acl_update: ACLRead, db: AsyncSession = Depends(get_db_session)):
    acl_update.id = id
    return await crud.upd(db, ACL, acl_update)


@acl.delete('/{id}')
async def delete_acl(id: UUID, db: AsyncSession = Depends(get_db_session)):
    success = await crud.delete(db, ACL, id)
    return get_delete_response(success, ACL.__tablename__)
