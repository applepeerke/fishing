from fastapi import HTTPException
from starlette import status
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.db import crud
from src.domains.login.acl.models import ACL
from src.domains.login.login.models import Login
from src.domains.login.role.models import Role
from src.domains.login.scope.functions import get_scope_name
from src.domains.login.scope.models import Scope, Access
from src.domains.login.token.functions import get_authentication
from src.domains.login.token.models import Authentication
from src.domains.login.user.models import User, UserStatus
from src.utils.functions import get_password_expiration
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.functions import get_user_from_db

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


async def login_with_fake_admin(
        db, clear_fake_db=True, response=None, email=None, password=None, role_names=None) -> Response:
    # Authorize user
    email = 'fakedummy@example.nl' if not email else email
    password = 'FakeWelcome01!' if not password else password
    role_names = ['fake_admin'] if not role_names else role_names
    authentication: Authentication = await _create_fake_authenticated_user(
        db, email, password, role_names, clear_fake_db=clear_fake_db)
    if not response:
        response = Response()
    response.headers.append(AUTHORIZATION, f'{authentication.token_type} {authentication.access_token}')
    return response


async def _create_fake_authenticated_user(db, email, password, role_names: list, clear_fake_db=True) -> Authentication:
    if not email or not password or not role_names:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail='Email, password and role name(s) are required.')

    if clear_fake_db:
        await _delete_item(db, User, User.email, email)
        [await _delete_item(db, Role, Role.name, name) for name in fake_roles]
        [await _delete_item(db, ACL, ACL.name, name) for name in fake_acls]
        [await _delete_item(db, Scope, Scope.scope_name, _get_scope_name(list(d.values()))) for d in fake_scopes]

    # Create fake Roles, with their ACLs and Scopes.
    roles: [Role] = await create_fake_role_set(db)

    # Get the specified role(s)
    filtered_roles = [role for role in roles if role.name in role_names]
    if not filtered_roles:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f'Roles "{role_names}" do not exist.')

    # Insert/replace the User as logged-in with certain role(s).
    return await _insert_logged_in_user(
        Login(email=email,
              password=password,
              password_repeat=password
              ),
        filtered_roles, db)


def _get_scope_name(values: list):
    return get_scope_name(values[0][0], values[0][1])


async def _delete_item(db, obj_def, att_name, att_value):
    item = await crud.get_one_where(db, obj_def, att_name, att_value)
    if item:
        await crud.delete(db, obj_def, item.id)


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


async def _insert_logged_in_user(credentials: Login, roles, db) -> Authentication:
    # Delete user
    user = await get_user_from_db(db, credentials.email)
    if user:
        await crud.delete(db, User, user.id)
    # Create user as LoggedIn
    user = User(
        email=credentials.email,
        password=get_salted_hash(credentials.password.get_secret_value()),
        password_expiration=get_password_expiration(),
        fail_count=0,
        status=UserStatus.LoggedIn,
        roles=roles
    )
    await crud.add(db, user)

    # Get Authentication.
    return await get_authentication(db, email=credentials.email, roles=roles)


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
