from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.db.db import get_db_session
from src.domains.login.acl.models import ACLRead, ACL
from src.domains.base.functions import get_delete_response
from src.domains.login.token.functions import is_authorized

acl = APIRouter()


@acl.post('/', response_model=ACLRead)
async def create_acl(
        acl_create: ACLRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['acl_create'])]
):
    new_acl = ACL(name=acl_create.name)
    return await crud.add(db, new_acl)


@acl.get('/', response_model=list[ACLRead])
async def read_acls(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['acls_readall'])],
        skip: int = 0,
        limit: int = 10,
):
    return await crud.get_all(db, ACL, skip=skip, limit=limit)


@acl.get('/{id}', response_model=ACLRead)
async def read_acl(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['acl_read'])]
):
    return await crud.get_one(db, ACL, id)


@acl.put('/{id}', response_model=ACLRead)
async def update_acl(
        id: UUID,
        acl_update: ACLRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['acl_update'])]
):
    acl_update.id = id
    return await crud.upd(db, ACL, acl_update)


@acl.delete('/{id}')
async def delete_acl(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['acl_delete'])]
):
    success = await crud.delete(db, ACL, id)
    return get_delete_response(success, ACL.__tablename__)
