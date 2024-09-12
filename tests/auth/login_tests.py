import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import test_data_login
from src.constants import PASSWORD, EMAIL, TOKEN, LOGIN, LOGOUT
from src.db import crud
from src.domains.user.models import User
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.constants import SUCCESS, PAYLOAD
from src.utils.tests.functions import post_check, get_leaf, get_json, get_model, get_user_from_db, get_check, \
    initialize_user_from_fixture, has_authorization_header
from tests.models.test_set import TestSet


@pytest.mark.asyncio
async def test_login_TDD(test_tdd_scenarios_login: dict, client: AsyncClient, db: AsyncSession):
    """
    TDD
    All test scenarios via csv file 'tests/tdd/automatic_tests_login.csv'.
    JSON fixtures are created dynamically via csv rows, not via .json files.
    """
    for Id, test_scenario in test_tdd_scenarios_login.items():
        for (r1, r2s) in test_scenario.items():
            for r2, r3s in r2s.items():
                for r3, results in r3s.items():
                    for result, fixture in results.items():
                        fixture_route = [Id, r1, r2, r3]
                        api_route = [i for i in fixture_route if i]
                        names = Id.split('|')  # seqno | precondition_userStatus | repeat | expected HTTP status
                        target_user_status = None if names[1] == 'NR' else int(names[1])
                        headers = {}
                        # Optionally insert User record with desired UserStatus
                        await initialize_user_from_fixture(
                            fixture_route, result, db, test_tdd_scenarios_login, target_user_status)
                        executions = int(names[2])
                        for exec_no in range(1, executions + 1):
                            await post_check(
                                api_route, test_tdd_scenarios_login, int(names[3]), client, db,
                                headers, fixture_route, route_from_index=1, check_response=exec_no == executions
                            )
                            print(f'* Test "{api_route[0]}" route "{' '.join(api_route[1:])}" was successful.')


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
    await get_check([LOGIN, 'acknowledge'], client, ts.params)
    # c. Override db OTP - forced hardcoded - towards hashed "Password1!"
    await change_password(db, ts.credentials)
    # d. Change password (from "Password1!" to "Password2!"). Status 10 -> 30.
    await post_check([PASSWORD, 'change'], ts.password_data, **kwargs)
    # e. Login (with "Password2!")
    response = await post_check([LOGIN], ts.login_data, **kwargs)
    assert has_authorization_header(response) is True
    # f. Logout
    kwargs['headers'] = [(k, v) for k, v in response.headers.items()]
    response = await post_check([LOGOUT], ts.logout_data, **kwargs)
    assert has_authorization_header(response) is False


@pytest.mark.asyncio
async def test_login_otp_success_after_fail(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    ts = get_test_set()
    kwargs = {'client': client, 'db': db}

    # 1. User requests OTP. Status 10.
    await post_check([LOGIN, 'register'], ts.login_data, 200, **kwargs)
    # 1.1 Override db random OTP - forced hardcoded - towards hashed "Password1!"
    await change_password(db, ts.credentials)
    # 2. User acknowledges - Simulate clicking the email link. Status 10 -> 20.
    await get_check([LOGIN, 'acknowledge'], client, ts.params)
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
    await get_check([LOGIN, 'acknowledge'], client, ts.params)
    # 3. User specifies max. number of wrong OTP.
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        response = await post_check([PASSWORD, 'change'], ts.password_data, 401, **kwargs)
        assert get_model(response) == {}
    # 4. User specifies another wrong one. Now expect user to be blocked. Status still 10.
    response = await post_check([PASSWORD, 'change'], ts.password_data, 401, **kwargs)
    #   No token should be returned
    assert has_authorization_header(response) is False


def get_test_set() -> TestSet:
    password_data = get_json(PASSWORD)
    credentials = get_test_credentials(password_data)
    test_set = TestSet()
    test_set.login_data = get_json(LOGIN)
    test_set.logout_data = get_json(LOGOUT)
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
    """ Token = token sent in acknowledge  email link query parameter. """
    fixture = get_leaf(fixture_set, [PASSWORD, 'change'], SUCCESS, PAYLOAD)
    return {EMAIL: fixture[EMAIL],
            PASSWORD: fixture[PASSWORD],
            TOKEN: get_salted_hash(fixture[EMAIL])}
