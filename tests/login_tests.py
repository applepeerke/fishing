import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import test_data_login
from src.constants import PASSWORD, EMAIL
from src.domains.user.functions import map_user
from src.domains.user.models import User
from src.db import crud
from src.utils.security.crypto import get_salted_hash
from src.utils.tests.constants import SUCCESS, PAYLOAD
from src.utils.tests.functions import post_check, get_leaf, get_json, get_model, get_user_from_db
from tests.functions import initialize_user_from_fixture, has_authorization_header


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
                                headers, fixture_route, route_from_index=1, check_response=exec_no == executions)
                            print(f'* Test "{api_route[0]}" route "{' '.join(api_route[1:])}" was successful.')


@pytest.mark.asyncio
async def test_register_success(test_data_login: dict, client: AsyncClient, db: AsyncSession):
    """ Target status Inactive (10) """
    api_route = ['login', 'register']
    await post_check(
        api_route, test_data_login, 200, client, db)


@pytest.mark.asyncio
async def test_register_fail(test_data_login: dict, client: AsyncClient, db: AsyncSession):
    api_route = ['login', 'register']
    await post_check(api_route, test_data_login, 422, client, db)


@pytest.mark.asyncio
async def test_login_happy_flow(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    login_data = test_data_login
    password_data = get_json(PASSWORD)
    kwargs = {'expected_http_status': 200, 'client': client, 'db': db}
    # a. Register - Send random OTP to user (mail is not really sent to user). Status 10.
    await post_check(['login', 'register'], login_data, **kwargs)
    # b. Override db OTP - forced hardcoded - to hashed "Password1!"
    await activate_user(db, get_test_credentials(password_data))
    # c. Change password (from "Password1!" to "Password2!"). Status 10 -> 30.
    await post_check([PASSWORD, 'change'], password_data, **kwargs)
    # d. Login (with "Password2!")
    response = await post_check(['login'], login_data, **kwargs)
    assert has_authorization_header(response) is True


@pytest.mark.asyncio
async def test_login_otp_success_after_fail(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    kwargs = {'client': client, 'db': db}
    login_data = test_data_login
    password_data = get_json(PASSWORD)
    # 1. User requests OTP. Status 10.
    await post_check(['login', 'register'], login_data, 200, **kwargs)
    # 1.1 Override db OTP - forced hardcoded - to hashed "Password1!"
    await activate_user(db, get_test_credentials(password_data))
    # 2. User specifies wrong OTP.
    response = await post_check([PASSWORD, 'change'], password_data, 401, **kwargs)
    #   No token should be returned
    assert has_authorization_header(response) is False
    # 3. User specifies right OTP. Status 10 -> 30.
    response = await post_check([PASSWORD, 'change'], password_data,  200, **kwargs)
    #   Token should be returned
    assert has_authorization_header(response) is True


@pytest.mark.asyncio
async def test_login_otp_fail(client: AsyncClient, db: AsyncSession, test_data_login: dict):
    """ Request otp, send wrong OTP (1 time too much). """
    kwargs = {'client': client, 'db': db}
    login_data = test_data_login
    password_data = get_json(PASSWORD)
    # 1. User requests OTP. Status 10.
    await post_check(['login', 'register'], login_data, 200, **kwargs)
    # 2. User specifies max. number of wrong OTP.
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        response = await post_check([PASSWORD, 'change'], password_data, 401, **kwargs)
        assert get_model(response) == {}
    # 3. User specifies another wrong one. Now expect user to be blocked. Status still 10.
    response = await post_check([PASSWORD, 'change'], password_data, 401, **kwargs)
    #   No token should be returned
    assert has_authorization_header(response) is False


async def activate_user(db, credentials: dict):
    """
    After registration, user is created with random OTP.
    Activate the user with the password from the password fixture.
    """

    """ Encrypt password and put it in the db. """
    user = await get_user_from_db(db, credentials[EMAIL])
    user.password = get_salted_hash(credentials[PASSWORD])
    await crud.upd(db, User, map_user(user))


def get_test_credentials(fixture_set):
    fixture = get_leaf(fixture_set, [PASSWORD, 'change'], SUCCESS, PAYLOAD)
    return {EMAIL: fixture[EMAIL], PASSWORD: fixture[PASSWORD]}
