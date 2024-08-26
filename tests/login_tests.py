import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.domains.user.models import User, UserStatus
from src.utils.db import crud
from src.utils.functions import get_pk, get_otp_expiration
from src.utils.security.crypto import get_random_password
from src.utils.tests.constants import SUCCESS, FAIL, PAYLOAD
from src.utils.tests.functions import post_check, get_leaf, set_password_in_db, get_model, set_leaf


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
    await precondition(breadcrumbs, SUCCESS, async_session, test_data_login, UserStatus.Active)
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_login)


@pytest.mark.asyncio
async def test_activate_fail(test_data_login: dict, async_client: AsyncClient, async_session: AsyncSession):
    breadcrumbs = ['login', 'activate']
    await precondition(breadcrumbs, FAIL, async_session, test_data_login, UserStatus.Active)
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login)


async def precondition(breadcrumbs, expected_status, db, fixture, user_status):
    fixture = get_leaf(fixture, breadcrumbs, expected_status)
    user = User(email=get_pk(fixture, 'email'), password=get_random_password(), expired=get_otp_expiration(),
                status=user_status)
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
    breadcrumbs = ['password', 'reset']
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
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login, seqno=1)
    # b. Change plain text to empty password
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_login, seqno=2, expected_http_status=422)


async def get_encrypted_text(breadcrumbs, async_client, async_session, fixture):
    # a. Encrypt (salt and hash) the plain_text password
    response = await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    response_payload = get_model(response)
    return response_payload.get('encrypted_text')
