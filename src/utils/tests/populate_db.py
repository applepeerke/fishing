from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import EMAIL, LOGIN
from src.db import crud
from src.domains.login.models import Login
from src.domains.role.models import Role
from src.domains.scope.models import Scope, Access
from src.domains.user.functions import map_user
from src.domains.user.models import User, UserStatus
from src.utils.functions import get_password_expiration
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.functions import get_user_from_db, post_to_endpoint


async def create_and_login_user(client: AsyncClient, db: AsyncSession):
    user = await _create_active_user(Login(EMAIL='dummy@example.nl', PASSWORD='Welcome01!'), db)
    kwargs = {'client': client, 'db': db}
    roles = await _create_roles(['admin', 'fisherman', 'fishingwater_manager'], db)
    scopes = await _create_scopes(
        {'admin_group': [['*', Access.all]],
         'fisherman_group': [['fish', Access.all], ['fishingwater', Access.read]],
        'fishingwater_manager_group': [['fishingwater', Access.all]]
         },  db)
    await create_scopes(**kwargs)
    await create_relations(**kwargs)
    # Login
    await post_to_endpoint(client, [LOGIN], login_credentials)


async def _create_active_user(credentials: Login, db) -> User:
    # Delete user
    user = await get_user_from_db(db, credentials[EMAIL])
    if user:
        await crud.delete(db, User, user.id)
    # Create user as Active
    user = User(
        email=credentials.email,
        password=get_salted_hash(credentials.password.get_secret_value()),
        expiration=get_password_expiration(),
        status=UserStatus.Active
    )
    return await crud.add(db, map_user(user))


async def _create_roles(roles: list, db) -> [Role]:
    [await crud.add(db, Role(name=role_name))
     for role_name in roles
     if not await crud.get_one_where(db, Role, Role.name, role_name)]
    return crud.get_all(db, Role)


async def _create_scopes(scopes: dict, db) -> [Scope]:
    [await crud.add(db, Scope(name=role_name))
     for scope in scopes
     if not await crud.get_one_where(db, Scope, Scope.name, role_name)]
    return crud.get_all(db, Scope)
