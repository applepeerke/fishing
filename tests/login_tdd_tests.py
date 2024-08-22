import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import map_user
from src.domains.user.models import User
from src.utils.db import crud
from src.utils.security.crypto import get_hashed_password
from src.utils.tests.functions import check_response


@pytest.mark.asyncio
async def test_register_user_success(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    await post_success(async_client, ['login', 'register'], test_data_login_tdd)


@pytest.mark.asyncio
async def test_register_user_fail(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    await post_fail(async_client, ['login', 'register'], test_data_login_tdd, 401)


async def post_success(client, breadcrumbs, test_data):
    """ Expect success. Precondition: JSON fixtures are defined by route, followed by "success". """
    # Get the "success"" fixture
    fixture = get_leaf(test_data, breadcrumbs)
    payload = fixture['success']['expect']
    response = await post_to_endpoint(client, breadcrumbs, payload)
    # Check
    check_response(
        response,
        expected_payload=payload,
        expected_status=status.HTTP_200_OK
    )


async def post_fail(client, breadcrumbs, test_data, expected_status):
    """ Expect failure. Precondition: JSON fixtures are defined by route, followed by "fail". """
    # Get the "fail"" fixture
    fixture = get_leaf(test_data, breadcrumbs)
    payload = fixture['fail']['expect']
    response = post_to_endpoint(client, breadcrumbs, payload)
    # Check
    check_response(
        response,
        expected_payload=payload,
        expected_status=expected_status
    )


async def post_to_endpoint(client, breadcrumbs, fixture):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    route = '/'.join(breadcrumbs[:-1])
    return await client.post(f'{route}/', json=fixture)


def get_leaf(fixture, breadcrumbs: list):
    d = fixture
    for leaf in breadcrumbs:
        d = d.get(leaf, {})
    return d


async def add_otp_from_db(db, test_data, endpoint):
    # - First set the test-otp from the db, which has been set to an unpredictable value.
    user = await get_user_from_db(db, test_data['login'][endpoint]['payload']['email'])
    test_data['login'][endpoint]['payload']['otp'] = user.otp
    return test_data


async def get_user_from_db(db, email):
    return await crud.get_one_where(db, User, User.email, email)


async def set_password_in_db(db, fixture, key):
    """ Encrypt password and put it in the db. """
    user = await get_user_from_db(db, fixture['email'])
    print(f'Old password to be hashed and set in db: {fixture[key]}')
    user.password = get_hashed_password(fixture[key])
    await crud.upd(db, User, user.id, map_user(user))

