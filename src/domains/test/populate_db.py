from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from src.constants import AUTHORIZATION
from src.db import crud
from src.db.db import get_db_session
from src.domains.acl.models import ACL
from src.domains.login.models import Login
from src.domains.role.models import Role
from src.domains.scope.models import Scope, Access
from src.domains.token.models import SessionToken
from src.domains.user.models import User, UserStatus
from src.session.session import create_authenticated_session
from src.utils.functions import get_password_expiration
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.functions import get_user_from_db

populate_fake_db = APIRouter()


@populate_fake_db.post('/')
async def create_and_login_user(response: Response, db: AsyncSession = Depends(get_db_session)):
    oauth2_token = await create_fake_db_with_authenticated_user(db)
    # - Update the response header
    response.headers.append(AUTHORIZATION, f'{oauth2_token.token_type} {oauth2_token.token}')


async def create_fake_db_with_authenticated_user(db, email='dummy@example.nl', password='Welcome01!') -> SessionToken:
    scopes = await _create_scopes(
        [
            {'admin': ['*', Access.all]},
         {'fisherman': ['fish', Access.all]},
         {'fisherman': ['fishingwater', Access.read]},
         {'fishingwater_manager': ['fishingwater', Access.all]}
        ], db)
    acls = await _create_acls(['admin_group', 'fisherman_group', 'fishingwater_manager_group'], scopes, db)
    roles = await _create_roles(['admin', 'fisherman', 'fishingwater_manager'], acls, db)
    # Login
    # - Create the user as logged in.
    login_credentials = Login(email=email, password=password, password_repeat=password)
    user = await _create_logged_in_user(login_credentials, roles, db)
    # - Authenticated the user in the session.
    return create_authenticated_session(user)


async def _create_logged_in_user(credentials: Login, roles, db) -> User:
    # Delete user
    user = await get_user_from_db(db, credentials.email)
    if user:
        await crud.delete(db, User, user.id)
    # Create user as Active
    user = User(
        email=credentials.email,
        password=get_salted_hash(credentials.password.get_secret_value()),
        expiration=get_password_expiration(),
        fail_count=0,
        status=UserStatus.LoggedIn,
        roles=roles
    )
    return await crud.add(db, user)


async def _create_roles(roles: list, acls, db) -> [Role]:
    [await crud.add(db, Role(name=role_name, acls=acls))
     for role_name in roles
     if not await crud.get_one_where(db, Role, Role.name, role_name)]
    return await crud.get_all(db, Role, relation=Role.acls)


async def _create_acls(acls: list, scopes, db) -> [ACL]:
    [await crud.add(db, ACL(name=acl, scopes=scopes))
     for acl in acls
     if not await crud.get_one_where(db, ACL, ACL.name, acl)]
    return await crud.get_all(db, ACL, relation=ACL.scopes)


async def _create_scopes(scopes: list, db) -> [Scope]:
    [await crud.delete(db, Scope, scope.id) for scope in await crud.get_all(db, Scope)]
    [await crud.add(db, Scope(entity=v[0], access=v[1])) for scope in scopes for k, v in scope.items()]
    return await crud.get_all(db, Scope)
