from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.db import crud
from src.db.db import get_db_session
from src.domains.acl.models import ACL
from src.domains.login.models import Login
from src.domains.role.models import Role
from src.domains.scope.models import Scope, Access
from src.domains.scope.scope_manager import ScopeManager
from src.domains.token.functions import get_authorization
from src.domains.token.models import Authorization
from src.domains.user.models import User, UserStatus
from src.utils.functions import get_password_expiration
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.functions import get_user_from_db

fake_user_login = APIRouter()

fake_scopes = [{'fake_admin': ['*', Access.all.value]},
               {'fake_fisherman': ['fake_fish', Access.all.value]},
               {'fake_fisherman': ['fake_fishingwater', Access.read.value]},
               {'fake_fishingwater_manager': ['fake_fishingwater', Access.all.value]}]

fake_acls = ['fake_admin_group',
             'fake_fisherman_group',
             'fake_fishingwater_manager_group']


fake_roles = ['fake_admin',
              'fake_fisherman',
              'fake_fishingwater_manager']


@fake_user_login.post('/')
async def login_with_fake_user(
        response: Response,
        db: AsyncSession = Depends(get_db_session),
        email='fakedummy@example.nl',
        password='FakeWelcome01!',
        role_name='fake_admin'
):
    # Authorize user
    authorization: Authorization = await get_fake_user_authorization(db, email, password, [role_name])
    response.headers.append(AUTHORIZATION, f'{authorization.token_type} {authorization.token}')


async def get_fake_user_authorization(db, email, password, role_names: list) -> Authorization:
    if not email or not password or not role_names:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Email, password and role name(s) are required.')

    # Create fake Roles, with their ACLs and Scopes.
    roles: [Role] = await create_fake_role_set(db)

    # Get the desired role(s)
    filtered_roles = [role for role in roles if role.name in role_names]
    if not filtered_roles:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'Roles "{role_names}" do not exist.')
    # Insert/replace the User as logged-in with certain role(s).
    return await _insert_logged_in_user(
        Login(email=email, password=password, password_repeat=password), filtered_roles, db)


async def create_fake_role_set(db) -> [Role]:
    # Create the fake Roles with their ACLs and Scopes.
    all_scopes = await _create_scopes(fake_scopes, db)
    all_acls = await _create_acls(fake_acls, all_scopes, db)
    return await _create_roles(fake_roles, all_acls, db)


async def add_user_roles(db, email, role_names: list):
    user = await get_user_from_db(db, email)
    roles = [await crud.get_one_where(db, Role, Role.name, role_name) for role_name in role_names]
    user.roles = roles
    await db.commit()


async def _insert_logged_in_user(credentials: Login, roles, db):
    # Delete user
    user = await get_user_from_db(db, credentials.email)
    if user:
        await crud.delete(db, User, user.id)
    # Create user as LoggedIn
    user = User(
        email=credentials.email,
        password=get_salted_hash(credentials.password.get_secret_value()),
        expiration=get_password_expiration(),
        fail_count=0,
        status=UserStatus.LoggedIn,
        roles=roles
    )
    await crud.add(db, user)

    # Get Authorization.
    sm = ScopeManager(db, credentials.email)
    scopes = await sm.get_user_scopes(roles)
    return get_authorization(email=credentials.email, scopes=scopes)


async def _create_roles(roles: list, acls, db) -> [Role]:
    [await crud.add(db, Role(name=role_name, acls=acls))
     for role_name in roles
     if not await crud.get_one_where(db, Role, Role.name, role_name)]
    return await crud.get_all(db, Role)


async def _create_acls(acls: list, scopes, db) -> [ACL]:
    [await crud.add(db, ACL(name=acl, scopes=scopes))
     for acl in acls
     if not await crud.get_one_where(db, ACL, ACL.name, acl)]
    return await crud.get_all(db, ACL)


async def _create_scopes(scopes: list, db) -> [Scope]:
    [await crud.delete(db, Scope, scope.id) for scope in await crud.get_all(db, Scope)]
    [await crud.add(db, Scope(entity=v[0], access=v[1])) for scope in scopes for k, v in scope.items()]
    return await crud.get_all(db, Scope)
