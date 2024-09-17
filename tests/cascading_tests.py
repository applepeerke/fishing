import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.role.models import Role
from src.domains.user.models import User


@pytest.mark.asyncio
async def test_cascading(client: AsyncClient, db: AsyncSession):
    """ No "cascading all, delete" is used in relationships because that deletes e.g. roles when a user is deleted."""
    # a. Create role-1 and role-2
    role_1 = await crud.add(db, Role(name='role_1'))
    assert role_1 is not None
    role_2 = await crud.add(db, Role(name='role_2'))
    assert role_2 is not None
    # b. create user-1 with both roles.
    user_1 = await add_user_with_roles(db, 'dummy-1@sample.com', roles=[role_1, role_2])
    assert user_1 and len(user_1.roles) == 2

    # c. Delete role-1
    await crud.delete(db, Role, user_1.roles[0].id)
    #    User 1 must still exist with 2 roles (unfortunately) - but table "user_role" has 1 link.
    user_1 = await crud.get_one(db, User, user_1.id)
    assert user_1 and len(user_1.roles) == 2
    #    Only role-2 must exist
    assert not await crud.get_one_where(db, Role, Role.name, 'role_1')
    assert await crud.get_one_where(db, Role, Role.name, 'role_2')

    # d. create user-2 with role-2
    user_2 = await add_user_with_roles(db, 'dummy-2@sample.com', roles=[role_2])

    # e. Delete user-1
    await crud.delete(db, User, user_1.id)
    assert not await crud.get_one(db, User, user_1.id)
    #    Role-2 must still exist
    roles = await crud.get_all(db, Role)
    assert len(roles) == 1

    # f. Delete user-2
    await crud.delete(db, User, user_2.id)
    assert not await crud.get_one(db, User, user_1.id)
    # There should still be 1 role.
    roles = await crud.get_all(db, Role)
    assert len(roles) == 1


async def add_user_with_roles(db, email, roles: list = None) -> User:
    # a. Create user
    user = await crud.add(db, User(email=email))
    assert user is not None
    # Add the roles to the user
    if roles:
        for role in roles:
            user.roles.append(role)
            await db.commit()
    # Verify
    user = await crud.get_one(db, User, user.id)
    assert len(user.roles) == len(roles) if roles else 0
    return user

