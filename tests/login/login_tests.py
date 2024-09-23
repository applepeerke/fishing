import datetime
import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import test_data_login
from src.constants import EMAIL, TOKEN
from src.db import crud
from src.domains.db_test.api import add_user_roles, create_fake_role_set
from src.domains.login.token.functions import session_login
from src.domains.login.user.models import User
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.constants import SUCCESS, PAYLOAD, LOGIN, PASSWORD, LOGOUT, FISHINGWATER
from src.utils.tests.expiration import Expiration
from src.utils.tests.functions import post_check, get_leaf, get_json, get_model, get_user_from_db, get_check, \
    has_authorization_header
from tests.models.test_set import TestSet


@pytest.mark.asyncio
async def test_register_success(test_data_login: dict, client: AsyncClient, db: AsyncSession):
    """ Target status Inactive (10) """
    api_route = [LOGIN, 'register']
    await post_check(
        api_route, test_data_login, 200, client, db)


@pytest.mark.asyncio
async def test_register_fail(test_data_login: dict, client: AsyncClient, db: AsyncSession):
    api_route = [LOGIN, 'register']
    await post_check(api_route, test_data_login, 422, client, db)


@pytest.mark.asyncio
async def test_login_happy_flow(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    ts = get_test_set()
    kwargs = {'expected_http_status': 200, 'client': client, 'db': db, 'headers': None}

    # a. Register - Send random OTP to user (mail is not really sent to user). Status 10.
    await post_check([LOGIN, 'register'], ts.login_data, **kwargs)
    # b. Acknowledge - Simulate user clicking the email link. Status 10 -> 20.
    await get_check([LOGIN, 'acknowledge'], client, params=ts.params)
    # c. Override db OTP - forced hardcoded - towards hashed "Password1!"
    await change_password(db, ts.credentials)
    # d. Change password (from "Password1!" to "Password2!"). Status 10 -> 30.
    await post_check([PASSWORD, 'change'], ts.password_data, **kwargs)
    # e. Authorize user (roles/acls/scopes).
    email = ts.login_data[LOGIN]['register'][SUCCESS][PAYLOAD][EMAIL]
    await create_fake_role_set(db)
    await add_user_roles(db, email, ['fake_fisherman'])
    # f. Login (with "Password2!")
    response = await post_check([LOGIN], ts.login_data, **kwargs)
    assert has_authorization_header(response) is True
    # g. Logout
    kwargs['headers'] = response.headers
    response = await post_check([LOGOUT], ts.logout_data, **kwargs)
    assert has_authorization_header(response) is False
    """
    Expiration-1: access=0, refresh=0
    """
    #  - Login again with access/refresh token expiration time 0 seconds/days.
    exp = Expiration(0, 0)
    response = await post_check([LOGIN], ts.login_data, **kwargs)
    await expect_expiration_days_around(db, email, exp)
    # - No read access to FishingWater (refresh token expired).
    await get_check([FISHINGWATER], client, 401, response.headers)
    """
    Expiration-2: access=0, refresh=30
    """
    # - Restore refresh_expiration to default (30 days)
    exp.reset_refresh_token_expiration()
    # - Session log in with updated authorization headers.
    user = await get_user_from_db(db, ts.credentials[EMAIL])
    response = await session_login(db, user)
    # 2. Read fishingwaters. This should cause the access token to be automatically refreshed from 0 to 3600 seconds.
    await get_check([FISHINGWATER], client, 200, response.headers)
    await expect_expiration_days_around(db, email, exp)


async def expect_expiration_days_around(db, email, exp):
    user = await crud.get_one_where(db, User, User.email, email)
    now = datetime.datetime.now(datetime.timezone.utc)
    if not user.refresh_token_expiration:
        delta = 0
    else:
        delta_expiration = user.refresh_token_expiration - now
        delta = delta_expiration.days - exp.refresh_token_expiration_days
    assert -1 <= delta <= 1


@pytest.mark.asyncio
async def test_login_otp_success_after_fail(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    ts = get_test_set()
    kwargs = {'client': client, 'db': db}

    # 1. User requests OTP. Status 10.
    await post_check([LOGIN, 'register'], ts.login_data, 200, **kwargs)
    # 1.1 Override db random OTP - forced hardcoded - towards hashed "Password1!"
    await change_password(db, ts.credentials)
    # 2. User acknowledges - Simulate clicking the email link. Status 10 -> 20.
    await get_check([LOGIN, 'acknowledge'], client, params=ts.params)
    # 3. User changes password - specifies wrong OTP.
    await post_check([PASSWORD, 'change'], ts.password_data, 401, **kwargs)
    # 4. User changes password - specifies right OTP. Status 20 -> 30.
    response = await post_check([PASSWORD, 'change'], ts.password_data, 200, **kwargs)
    #   No token should be returned
    assert has_authorization_header(response) is False


@pytest.mark.asyncio
async def test_login_otp_fail(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    """ Request otp, send wrong OTP (1 time too much). """
    ts = get_test_set()
    kwargs = {'client': client, 'db': db}

    # 1. User requests OTP. Status 10.
    await post_check([LOGIN, 'register'], ts.login_data, 200, **kwargs)
    # 2. User acknowledges - Simulate clicking the email link. Status 10 -> 20.
    await get_check([LOGIN, 'acknowledge'], client, params=ts.params)
    # 3. User specifies max. number of wrong OTP.
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        response = await post_check([PASSWORD, 'change'], ts.password_data, 401, **kwargs)
        assert get_model(response) == {}
    # 4. User specifies another wrong one. Now expect user to be blocked. Status still 10.
    response = await post_check([PASSWORD, 'change'], ts.password_data, 401, **kwargs)
    #   No access token should be returned.
    assert has_authorization_header(response) is False


def get_test_set() -> TestSet:
    password_data = get_json(PASSWORD)
    credentials = get_test_credentials(password_data)
    test_set = TestSet()
    test_set.login_data = get_json(LOGIN)
    test_set.logout_data = get_json(LOGOUT)
    test_set.fishingwater_data = get_json(FISHINGWATER)
    test_set.password_data = password_data
    test_set.credentials = credentials
    test_set.params = {EMAIL: credentials[EMAIL], TOKEN: credentials[TOKEN]}
    return test_set


async def change_password(db, credentials: dict):
    """ Encrypt password and put it in the db. """
    user = await get_user_from_db(db, credentials[EMAIL])
    user.password = get_salted_hash(credentials[PASSWORD])
    await crud.upd(db, User, user)


def get_test_credentials(fixture_set):
    """ Token = token sent in acknowledge email link query parameter. """
    fixture = get_leaf(fixture_set, [PASSWORD, 'change'], SUCCESS, PAYLOAD)
    return {EMAIL: fixture[EMAIL],
            PASSWORD: fixture[PASSWORD],
            TOKEN: get_salted_hash(fixture[EMAIL])}
