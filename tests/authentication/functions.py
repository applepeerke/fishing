from http import HTTPStatus

from httpx import AsyncClient
from starlette.responses import Response

from src.domains.login.models import Login
from src.domains.token.constants import BEARER
from src.domains.token.functions import get_user_status
from src.domains.user.functions import map_user
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.functions import get_pk
from src.utils.security.crypto import get_random_password, get_salted_hash
from src.utils.tests.constants import PAYLOAD, AUTHORIZATION
from src.utils.tests.functions import get_leaf


async def login_user(username, plain_text_password, db, client: AsyncClient) -> Response:
    """ Create/update user and add Authorization header to the response. """
    # Updert user with the right UserStatus
    user = await _initialize_user(db, username, UserStatus.Active, plain_text_password)
    if not user:
        raise ValueError('User could not be upderted in the database.')
    # Login to get the authorization header
    response = await client.post(f'login/', json={'email': user.email, 'password': plain_text_password})
    return response


def has_authorization_header(response):
    return any(header == AUTHORIZATION.lower() for header in response.headers)


def get_authorization_header(response) -> dict:
    for header, authorization in response.headers.items():
        if header == AUTHORIZATION.lower() and authorization.startswith(BEARER):
            return {AUTHORIZATION: authorization}


async def initialize_user_from_fixture(api_route, expected_status, db, fixture, user_status: int | None):
    """ Update UserStatus or add or delete a user """
    fixture = get_leaf(fixture, api_route, expected_status)
    plain_text_password = fixture.get(PAYLOAD, {}).get('password')
    if plain_text_password and 'right' not in plain_text_password.lower():
        plain_text_password = None
    await _initialize_user(db, get_pk(fixture, 'email'), user_status, plain_text_password)


async def _initialize_user(db, pk, target_status: int | None, plain_text_password=None) -> User | None:
    """ Initialize user from a target UserStatus. """
    if not pk:
        return
    user_old = await crud.get_one_where(db, User, att_name=User.email, att_value=pk)
    # a. Delete user (if no target status)
    if user_old and target_status is None:
        await crud.delete(db, User, user_old.id)
        return
    # b. Set attributes
    # - Status related attributes
    user = get_user_status(User(email=pk, fail_count=0), target_status)
    # - Password
    if not plain_text_password and target_status > 10:
        plain_text_password = get_random_password()
    user.password = get_salted_hash(plain_text_password)
    # c. Updert user
    if user_old:
        user.id = user_old.id
        return await crud.upd(db, User, map_user(user))
    else:
        return await crud.add(db, user)
