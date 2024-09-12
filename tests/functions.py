import datetime

from src.constants import AUTHORIZATION
from src.db import crud
from src.domains.token.constants import BEARER
from src.domains.user.functions import set_user_status_related_attributes
from src.domains.user.models import User, UserStatus
from src.utils.functions import get_pk
from src.utils.security.crypto import get_random_password, get_salted_hash
from src.utils.tests.constants import PAYLOAD
from src.utils.tests.functions import get_leaf


def has_authorization_header(response):
    return any(header == AUTHORIZATION for header in response.headers)


def get_authorization_header(response) -> dict:
    for header, authorization in response.headers.items():
        if header == AUTHORIZATION and authorization.startswith(BEARER):
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
    user = set_user_status_related_attributes(User(email=pk, fail_count=0), target_status)
    # - Password
    if not plain_text_password and target_status > 10:
        plain_text_password = get_random_password()
    user.password = get_salted_hash(plain_text_password)
    if target_status == UserStatus.Expired:
        user.expiration = datetime.datetime.now(datetime.timezone.utc)
    # c. Updert user
    if user_old:
        user.id = user_old.id
        return await crud.upd(db, User, user)
    else:
        return await crud.add(db, user)
