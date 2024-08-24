import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.login.functions import map_user
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_hashed_password, get_otp_as_number
from src.utils.tests.functions import assert_response, get_model
from tests.data.constants import SUCCESS, FAIL, PAYLOAD, EXPECT_DB, \
    EXPECT, STRING, GET_FROM_DB, GT0

fixture_base = 'login'

# ToDo: DB status can not be checked after http_exception. "crud.get_one" returns old data, even if it is committed.


@pytest.mark.asyncio
async def test_register_success(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Status Registered (10) """
    await _post_check('register', SUCCESS, async_client, async_session, test_data_login_tdd)


@pytest.mark.asyncio
async def test_register_fail(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    await _post_check('register', FAIL, async_client, async_session, test_data_login_tdd)


@pytest.mark.asyncio
async def test_initialize_success(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Status Initialized (20) """
    add_user = User(otp=get_otp_as_number(), expired=get_otp_expiration(), status=UserStatus.Registered)
    await _post_check(
        'initialize', SUCCESS, async_client, async_session, test_data_login_tdd, user_to_add=add_user)


@pytest.mark.asyncio
async def test_initialize_fail(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    add_user = User(otp=get_otp_as_number(), expired=get_otp_expiration(), status=UserStatus.Registered)
    await _post_check('initialize', FAIL, async_client, async_session, test_data_login_tdd, user_to_add=add_user)


@pytest.mark.asyncio
async def test_activate_success(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Status Activated (30) """
    add_user = User(otp=get_otp_as_number(), expired=get_otp_expiration(), status=UserStatus.Initialized)
    await _post_check('activate', SUCCESS, async_client, async_session, test_data_login_tdd, user_to_add=add_user)


@pytest.mark.asyncio
async def test_activate_fail(test_data_login_tdd: dict, async_client: AsyncClient, async_session: AsyncSession):
    add_user = User(otp=get_otp_as_number(), expired=get_otp_expiration(), status=UserStatus.Initialized)
    await _post_check('activate', FAIL, async_client, async_session, test_data_login_tdd, user_to_add=add_user)


async def _post_check(
        endpoint_leaf, expected_result, client, db, test_data, expected_http_status=None, user_to_add=None):
    """ Precondition: JSON fixtures are defined by route, followed by 'success' or 'fail'. """
    if not expected_http_status:
        expected_http_status = status.HTTP_200_OK if expected_result == SUCCESS else status.HTTP_401_UNAUTHORIZED
    breadcrumbs = [fixture_base, endpoint_leaf]
    fixture = _get_leaf(test_data, breadcrumbs, expected_result)
    # After every test run the database is empty.
    if user_to_add:
        user_to_add.email = fixture.get(PAYLOAD, {}).get('email')
        await crud.add(db, user_to_add)

    payload = await _substitute(db, fixture.get(PAYLOAD))
    response = await _post_to_endpoint(
        client=client,
        breadcrumbs=breadcrumbs,
        fixture=payload
    )
    # a. Check response (model or exception)
    assert_response(
        response,
        expected_payload=fixture.get(EXPECT),
        expected_status=expected_http_status
    )
    # b. Check db attributes
    # Db can be checked only if the response is OK.
    # In case of an exception, the db record may have been updated but can not be retrieved here. Why?
    if get_model(response):
        await _assert_db(db, fixture.get(EXPECT_DB))


async def _assert_db(db, expected_payload):
    if not expected_payload:
        return

    expected_payload = await _substitute(db, expected_payload)
    user = await crud.get_one_where(db, User, User.email, expected_payload['email'])
    # Assertions
    assert user.email == expected_payload['email']
    assert user.password == expected_payload['password']
    if expected_payload['otp'] == GT0:
        assert user.otp > 0
    else:
        assert user.otp == expected_payload['otp']
    if user.otp or expected_payload['password'] == STRING:
        _validate_expiration(user.expired)
    if expected_payload['password'] != STRING:
        assert user.password is None
    assert user.fail_count == expected_payload['fail_count']
    assert user.status == expected_payload['status']


def _validate_expiration(db_expiration, delta_seconds_allowed=10.0):
    """ Precondition: db_expiration has been set < 1 second ago. """
    assert db_expiration is not None
    now_expiration = get_otp_expiration()
    delta = now_expiration - db_expiration
    assert 0.0 < delta.total_seconds() < delta_seconds_allowed


async def _post_to_endpoint(client, breadcrumbs, fixture):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    route = '/'.join(breadcrumbs)
    return await client.post(f'{route}/', json=fixture)


def _get_leaf(fixture, breadcrumbs: list, expected_result):
    d = fixture
    for leaf in breadcrumbs:
        d = d.get(leaf, {})
    return d.get(expected_result, {})


async def _substitute(db, fixture) -> dict:
    """ Substitute unpredictable attribute values from those in the db. """
    if any(v == GET_FROM_DB for v in fixture.values()):
        user = await get_user_from_db(db, fixture.get('email'))
        if user:
            fixture = {k: _try_substitute(k, v, user) for k, v in fixture.items()}
    return fixture


def _try_substitute(key, value, user):
    if value == GET_FROM_DB:
        if key == 'otp':
            value = user.otp
    return value


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

