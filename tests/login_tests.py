import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from conftest import test_data_login
from src.domains.user.functions import map_user
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.functions import get_pk, get_otp_expiration
from src.utils.security.crypto import get_otp, get_salted_hash
from src.utils.tests.constants import SUCCESS, PAYLOAD
from src.utils.tests.functions import post_check, get_leaf, set_password_in_db


@pytest.mark.asyncio
async def test_login_TDD(test_tdd_scenarios_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """
    TDD
    All test scenarios via csv file 'tests/tdd/login.csv'.
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
                        # Optionally insert User record with desired UserStatus
                        await precondition(fixture_route, result, async_session, test_tdd_scenarios_login,
                                           target_user_status)
                        executions = int(names[2])
                        for exec_no in range(1, executions + 1):
                            await post_check(
                                api_route, int(names[3]), async_client, async_session, test_tdd_scenarios_login,
                                fixture_route, route_from_index=1, check_response=exec_no == executions)
                            print(f'* Test "{api_route[0]}" route "{' '.join(api_route[1:])}" was successful.')


@pytest.mark.asyncio
async def test_register_success(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Target status Inactive (10) """
    api_route = ['user', 'login', 'register']
    await post_check(
        api_route, 200, async_client, async_session, test_data_login)


@pytest.mark.asyncio
async def test_register_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    api_route = ['user', 'login', 'register']
    await post_check(api_route, 422, async_client, async_session, test_data_login)


async def precondition(api_route, expected_status, db, fixture, user_status: UserStatus | None):
    """ Update UserStatus or add or delete a user """
    fixture = get_leaf(fixture, api_route, expected_status)
    pk = get_pk(fixture, 'email')
    if not pk:
        return
    user_old = await crud.get_one_where(db, User, att_name=User.email, att_value=pk)
    # a. Delete user (if target is NR)
    if user_old and not user_status:
        await crud.delete(db, User, user_old.id)
        return
    # b. Set attributes
    # - Password: set the right or a random one.
    password = fixture.get(PAYLOAD, {}).get('password')
    password = get_salted_hash(password) \
        if password and 'right' in password.lower() \
        else get_otp()

    user = User(email=pk, password=password, expired=get_otp_expiration(),
                fail_count=0, status=user_status)
    if user_old:
        # c. Update user
        user.id = user_old.id
        await crud.upd(db, User, user_old.id, map_user(user))

    else:
        # d. Add user
        await crud.add(db, user)


@pytest.mark.asyncio
async def test_login_happy_flow(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    kwargs = {'expected_http_status': 200, 'client': async_client, 'db': async_session, 'fixture': test_data_login}
    api_route = ['user', 'login', 'register']
    # a. Register - request otp
    await post_check(api_route, **kwargs)
    # b. Change db OTP (to hashed "Password1!")
    await change_password(async_session, test_data_login)
    # c. Change password (to "Password2!")
    api_route = ['user', 'password', 'change']
    await post_check(api_route, **kwargs)
    # d. Login (with "Password2!")
    api_route = ['user', 'login']
    await post_check(api_route, **kwargs)


@pytest.mark.asyncio
async def test_login_otp_fail(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    kwargs = {'client': async_client, 'db': async_session, 'fixture': test_data_login}
    # Register
    api_route = ['user', 'login', 'register']
    # a.  Send OTP to user (mail is not really sent to user).
    await post_check(api_route, 200, **kwargs)
    # a.1 Change db OTP (to hashed "Password1!")
    await change_password(async_session, test_data_login)
    # a.2 User specifies wrong OTP.
    api_route = ['user', 'password', 'change']
    await post_check(api_route, 401, **kwargs)
    # a.3 User specifies right OTP.
    await post_check(api_route, 200, **kwargs)

    # b. request otp, send wrong OTP (1 time too much).
    # b.1 delete the user
    fixture = get_leaf(test_data_login, api_route, SUCCESS)
    user = await crud.get_one_where(async_session, User, att_name=User.email, att_value=fixture['payload']['email'])
    await crud.delete(async_session, User, user.id)
    # b.2 request OTP.
    api_route = ['user', 'login', 'register']
    await post_check(api_route, 200, **kwargs)
    # b.3 User sends max. number of wrong OTP.
    api_route = ['user', 'password', 'change']
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        await post_check(api_route, 401, **kwargs)
    # b.4 Send another wrong one. Now expect user to be blocked.
    await post_check(api_route, 401, **kwargs)


async def change_password(async_session, test_data_login):
    """ After registration, user is created with random OTP, reset it with the one from the fixture. """
    api_route = ['user', 'password', 'change']
    fixture = get_leaf(test_data_login, api_route, SUCCESS)
    await set_password_in_db(async_session, fixture[PAYLOAD], 'password')
