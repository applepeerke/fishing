import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import map_user
from src.domains.user.models import User
from src.utils.db import crud
from src.utils.functions import get_expired_otp, get_expired_password
from src.utils.security.crypto import get_hashed_password
from src.utils.tests.functions import check_response
from tests.data.constants import CALC_EXPIRED_OTP, CALC_EXPIRED_PASSWORD, GT0


@pytest.mark.asyncio
async def test_register_user_success(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'register']
    await post_success(async_client, async_session, breadcrumbs, test_data_login_tdd)


@pytest.mark.asyncio
async def test_register_user_fail(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'register']
    await post_fail(async_client, async_session, breadcrumbs, test_data_login_tdd, 401)


async def post_success(client, db, breadcrumbs, test_data):
    """ Expect success. Precondition: JSON fixtures are defined by route, followed by "success". """
    await post_check(client, db, breadcrumbs, test_data, 'success', status.HTTP_200_OK)


async def post_fail(client, db, breadcrumbs, test_data, expected_status):
    """ Expect failure. Precondition: JSON fixtures are defined by route, followed by "fail". """
    await post_check(client, db, breadcrumbs, test_data, 'fail', expected_status)


async def post_check(client, db, breadcrumbs, test_data, expected_result, expected_status):
    fixture = get_leaf(test_data, breadcrumbs)
    payload = fixture[expected_result]['expect']
    response = await post_to_endpoint(client, breadcrumbs, payload)
    # Check
    check_response(
        response,
        expected_payload=payload,
        expected_status=expected_status
    )
    # Check_db
    payload = fixture[expected_result]['expect_db']
    user = await crud.get_one_where(db, User, User.email, payload['email'])
    # Check attributes
    # - Substitutions
    if payload['expired'] == CALC_EXPIRED_OTP:
        payload['expired'] = get_expired_otp()
    elif payload['expired'] == CALC_EXPIRED_PASSWORD:
        payload['expired'] = get_expired_password()

    assert user.email == payload['email']
    assert user.password == payload['password']
    if payload['otp'] == GT0:
        assert user.otp > 0
    else:
        assert user.otp is None
    if payload['expired'] is None:
        assert user.expired is None
    else:
        # ToDo: calculate expiration
        assert user.expired is not None
    assert user.fail_count == payload['fail_count']
    assert user.status == payload['status']


async def post_to_endpoint(client, breadcrumbs, fixture):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    route = '/'.join(breadcrumbs)
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

