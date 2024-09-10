import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.role.models import Role
from src.domains.user.models import User


@pytest.mark.asyncio
async def test_cascading(client: AsyncClient, db: AsyncSession):
    # a. Create user
    user = await crud.add(db, User(email=os.getenv('TEST_MAIL_ADDRESS')))
    assert user is not None
    # b. Create role-1
    role_1 = await crud.add(db, Role(name='role_1', user_id=user.id))
    assert role_1 is not None
    # c. Create role-2
    role_2 = await crud.add(db, Role(name='role_2', user_id=user.id))
    assert role_2 is not None
    # d. Delete role-1
    await crud.delete(db, Role, role_1.id)
    # e. User must still exist
    assert await crud.get_one_where(db, User, User.email, user.email)
    # f. Only role_2 must exist
    assert not await crud.get_one_where(db, Role, Role.name, 'role_1')
    assert await crud.get_one_where(db, Role, Role.name, 'role_2')
    # g. Delete user
    await crud.delete(db, User, user.id)
    assert not await crud.get_one_where(db, User, User.email, user.email)
    # i. Read role
    roles = await crud.get_all(db, Role)
    assert not roles
