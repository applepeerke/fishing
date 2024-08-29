import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.login.functions import map_user
from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.functions import get_pk, get_otp_expiration
from src.utils.security.crypto import get_random_password, get_hashed_password
from src.utils.tests.constants import SUCCESS, FAIL, PAYLOAD
from src.utils.tests.functions import post_check, get_leaf, set_password_in_db, get_model, set_leaf


@pytest.mark.asyncio
async def test_login_TDD(test_tdd_scenarios_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """
    TDD
    All test scenarios via csv file 'tests/tdd/login.csv'.
    JSON fixtures are created dynamically via csv rows, not via .json files.
    """
    for Id, test_scenario in test_tdd_scenarios_login.items():
        for entity, endpoints in test_scenario.items():
            for endpoint, results in endpoints.items():
                for result, fixture in results.items():
                    breadcrumbs = [Id, entity, endpoint]
                    names = Id.split('|')  # seqno | precondition_userStatus | repeat | expected HTTP status
                    target_user_status = -1 if names[1] == 'NR' else int(names[1])
                    # Optionally insert User record with desired UserStatus
                    await precondition(breadcrumbs, result, async_session, test_tdd_scenarios_login, target_user_status)
                    executions = int(names[2])
                    for exec_no in range(1, executions + 1):
                        await post_check(
                            breadcrumbs, result, async_client, async_session, test_tdd_scenarios_login,
                            expected_http_status=int(names[3]), check_response=exec_no == executions,
                            from_index=1)
                        print(f'* Test "{breadcrumbs[0]}" route "{' '.join(breadcrumbs[1:])}" was successful.')


@pytest.mark.asyncio
async def test_register_success(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Target status Inactive (10) """
    breadcrumbs = ['login', 'register']
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)


@pytest.mark.asyncio
async def test_register_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'register']
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login, 422)


@pytest.mark.asyncio
async def test_activate_success(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Target status Activated (20) """
    breadcrumbs = ['login', 'activate']
    await precondition(breadcrumbs, SUCCESS, async_session, test_data_login, UserStatus.Active.value)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)


@pytest.mark.asyncio
async def test_activate_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'activate']
    await precondition(breadcrumbs, FAIL, async_session, test_data_login, UserStatus.Active.value)
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login)


async def precondition(breadcrumbs, expected_status, db, fixture, user_status: int):
    """ Update UserStatus or add or delete a user """
    fixture = get_leaf(fixture, breadcrumbs, expected_status)
    pk = get_pk(fixture, 'email')
    if not pk:
        return
    user_old = await crud.get_one_where(db, User, att_name=User.email, att_value=pk)
    # a. Delete user (if target is NR)
    if user_old and user_status <= 0:
        await crud.delete(db, User, user_old.id)
        return
    # b. Set attributes
    # - Password: set the right or a random one.
    password = fixture.get(PAYLOAD, {}).get('password')
    password = get_hashed_password(password) \
        if password and 'right' in password.lower() \
        else get_random_password()

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
    # a. Register - request otp
    breadcrumbs = ['login', 'register']
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)

    # b. Register - send otp
    breadcrumbs = ['login', 'activate']
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)

    # c. Change password
    # c1. Preparation: Put old password in db ("Password1!")
    breadcrumbs = ['password', 'set']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await set_password_in_db(async_session, fixture[PAYLOAD], 'password')
    # c2. Change new password (to "Password2!")
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)

    # d. Login (with "Password2!")
    breadcrumbs = ['login', 'login']
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)


@pytest.mark.asyncio
async def test_login_otp_fail(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # Register
    breadcrumbs = ['login', 'register']
    # a.1 request otp.
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)
    # a.2 send wrong otp.
    breadcrumbs = ['login', 'activate']
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login, 401)
    # a.3 send right otp.
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)

    # b. request otp, send wrong otp (1 time too much).
    # b.1 delete the user
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    user = await crud.get_one_where(async_session, User, att_name=User.email, att_value=fixture['payload']['email'])
    await crud.delete(async_session, User, user.id)
    # b.2 request otp.
    breadcrumbs = ['login', 'register']
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)
    # b.3 User sends max. number of wrong otp.
    breadcrumbs = ['login', 'activate']
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login)
    # b.4 Send another wrong one. Now expect user to be blocked.
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login)


@pytest.mark.asyncio
async def test_encrypt(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # Success
    # a. Calculate encryption and add it to payload
    breadcrumbs = ['encrypt']
    encrypted_text = await get_encrypted_text(breadcrumbs, async_client, async_session, test_data_login)
    # b. Add encrypted_text to payload
    breadcrumbs = ['encrypt', 'verify']
    test_data_login = set_leaf(test_data_login, breadcrumbs, SUCCESS, PAYLOAD, 'encrypted_text', encrypted_text)
    # c Decrypt the encrypted text and compare with the input plain text
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)

    # Fail
    # a. Change plain text to invalid password
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login, seq_no=1)
    # b. Change plain text to empty password
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login, seq_no=2, expected_http_status=422)


async def get_encrypted_text(breadcrumbs, async_client, async_session, fixture):
    # a. Encrypt (salt and hash) the plain_text password
    response = await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    response_payload = get_model(response)
    return response_payload.get('encrypted_text')
