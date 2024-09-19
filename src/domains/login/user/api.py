from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.base.functions import get_delete_response
from src.domains.login.token.functions import is_authorized
from src.domains.login.user.models import User, UserRead, UserCreate
from src.db import crud
from src.db.db import get_db_session

user = APIRouter()


@user.post('/', response_model=UserRead)
async def create_user(
        user_create: UserCreate,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['user_create'])]
):
    new_user = User(email=user_create.email)
    return await crud.add(db, new_user)


@user.get('/', response_model=list[UserRead])
async def read_users(
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['user_readall'])],
        skip: int = 0,
        limit: int = 10
):
    return await crud.get_all(db, User, skip=skip, limit=limit)


@user.get('/{id}', response_model=UserRead)
async def read_user(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['user_read'])]
):
    return await crud.get_one(db, User, id)


@user.put('/{id}', response_model=UserRead)
async def update_user(
        id: UUID, user_update: UserRead,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['user_update'])]
):
    user_update.id = id
    return await crud.upd(db, User, user_update)


@user.delete('/{id}')
async def delete_user(
        id: UUID,
        db: Annotated[AsyncSession, Depends(get_db_session)],
        _: Annotated[bool, Security(is_authorized, scopes=['user_delete'])]
):
    success = await crud.delete(db, User, id)
    return get_delete_response(success, User.__tablename__)
