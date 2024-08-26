import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.functions import get_pk, get_otp_expiration
from src.utils.security.crypto import get_otp_as_number
from src.utils.tests.constants import SUCCESS, FAIL, PAYLOAD
from src.utils.tests.functions import assert_response, post_check, get_leaf, set_password_in_db, get_model


@pytest.mark.asyncio
async def test_register_success(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Target status Inactive (10) """
    breadcrumbs = ['login', 'register']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_register_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'register']
    fixture = get_leaf(test_data_login, breadcrumbs, FAIL)
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_initialize_success(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Target status Initialized (20) """
    breadcrumbs = ['login', 'initialize']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await precondition(async_session, fixture, UserStatus.Registered)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_initialize_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'initialize']
    fixture = get_leaf(test_data_login, breadcrumbs, FAIL)
    await precondition(async_session, fixture, UserStatus.Registered)
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_activate_success(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    """ Target status Activated (30) """
    breadcrumbs = ['login', 'activate']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await precondition(async_session, fixture, UserStatus.Initialized)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_activate_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'activate']
    fixture = get_leaf(test_data_login, breadcrumbs, FAIL)
    await precondition(async_session, fixture, UserStatus.Initialized)
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture)


async def precondition(db, fixture, user_status):
    user = User(email=get_pk(fixture, 'email'), otp=get_otp_as_number(), expired=get_otp_expiration(),
                status=user_status)
    await crud.add(db, user)


@pytest.mark.asyncio
async def test_login_happy_flow(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a. Register - request otp
    breadcrumbs = ['login', 'register']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)

    # b. Register - send otp
    breadcrumbs = ['login', 'initialize']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)

    # c. Change password
    # c1. Preparation: Put old password in db ("Password1!")
    breadcrumbs = ['password', 'reset']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await set_password_in_db(async_session, fixture[PAYLOAD], 'old_password')
    # c2. Change new password (to "Password2!")
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)

    # d. Login (with "Password2!")
    breadcrumbs = ['login', 'login']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_login_otp_fail(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # Register
    breadcrumbs = ['login', 'register']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    # a.1 request otp.
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    # a.2 send wrong otp.
    breadcrumbs = ['login', 'initialize']
    fixture = get_leaf(test_data_login, breadcrumbs, FAIL)
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture, 401)
    # a.3 send right otp.
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)

    # b. request otp, send wrong otp (1 time too much).
    # b.1 delete the user
    user = await crud.get_one_where(async_session, User, att_name=User.email, att_value=fixture['payload']['email'])
    await crud.delete(async_session, User, user.id)
    # b.2 request otp.
    breadcrumbs = ['login', 'register']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    # b.3 User sends max. number of wrong otp.
    breadcrumbs = ['login', 'initialize']
    fixture = get_leaf(test_data_login, breadcrumbs, FAIL)
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        await post_check(breadcrumbs, FAIL, async_client, async_session, fixture)
    # b.4 Send another wrong one. Now expect user to be blocked.
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture)


@pytest.mark.asyncio
async def test_encrypt(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # Success
    # a. Encrypt (salt and hash) the plain_text password
    breadcrumbs = ['encrypt', 'verify']
    fixture = get_leaf(test_data_login, breadcrumbs, SUCCESS)
    # b. Calculate encryption and add it to payload
    breadcrumbs = ['encrypt']
    fixture[PAYLOAD]['encrypted_text'] = await get_encrypted_text(breadcrumbs, async_client, async_session, fixture)
    # c Decrypt the encrypted text and compare with the input plain text
    breadcrumbs = ['encrypt', 'verify']
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    # Fail
    # a. Change plain text to invalid password
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture, seqno=1)
    # b. Change plain text to empty password
    await post_check(breadcrumbs, FAIL, async_client, async_session, fixture, seqno=2, expected_http_status=422)


async def get_encrypted_text(breadcrumbs, async_client, async_session, fixture):
    # a. Encrypt (salt and hash) the plain_text password
    response = await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    response_payload = get_model(response)
    return response_payload.get('encrypted_text')
