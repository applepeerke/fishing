import os

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
async def test_login_happy_flow(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a. Register - request otp
    await post_to_endpoint(async_client, ['login', 'register'], test_data_login)
    # b. Register - send otp
    test_data = await add_otp_from_db(async_session, test_data_login, 'validate')
    await post_to_endpoint(async_client, ['login', 'validate'], test_data)
    # c. Change password
    # c1. Preparation: Put old password in db ("Password1!")
    await set_password_in_db(async_session, test_data['password']['reset']['payload'], 'old_password')
    # c2. Change new password (to "Password2!")
    await post_to_endpoint(async_client, ['password', 'reset'], test_data)
    # d. Login (with "Password2!")
    await post_to_endpoint(async_client, ['login', 'login'], test_data)


@pytest.mark.asyncio
async def test_login_otp_fail(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a.1 request otp.
    await post_to_endpoint(async_client, ['login', 'register'], test_data_login)
    # a.2 send wrong otp.
    await post_to_endpoint(
        async_client,['login', 'validate'], test_data_login,
        'payload_fail', 'expect_fail-1', 401)
    # a.3 send right otp.
    test_data = await add_otp_from_db(async_session, test_data_login, 'validate')
    await post_to_endpoint(async_client, ['login', 'validate'], test_data)

    # b. request otp, send wrong otp (1 time too much).
    # b.1 delete the user
    user = await crud.get_one_where(async_session, User,
                                    att_name=User.email, att_value=test_data['login']['register']['payload']['email'])
    await crud.delete(async_session, User, user.id)
    # b.2 request otp.
    await post_to_endpoint(async_client, ['login', 'register'], test_data_login)
    # b.3 User sends max. number of wrong otp.
    for i in range(int(os.getenv('LOGIN_FAILING_ATTEMPTS_ALLOWED')) - 1):
        await post_to_endpoint(
            async_client, ['login', 'validate'], test_data,
            'payload_fail', 'expect_fail-1', 401)
    # b.4 Send another wrong one. Now expect user to be blocked.
    await post_to_endpoint(
        async_client, ['login', 'validate'], test_data,
        'payload_fail', 'expect_fail-2', 401)


async def post_to_endpoint(
        async_client, breadcrumbs, test_data, payload_key='payload', expect_key='expect', expected_status=200):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    # Get the leaf fixture
    fixture = get_leaf(test_data, breadcrumbs)
    # Post
    route = '/'.join(breadcrumbs)
    response = await async_client.post(f'{route}/', json=fixture[payload_key])
    # Check
    check_response(
        response,
        expected_payload=fixture.get(expect_key, {}),
        expected_status=expected_status
    )


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


@pytest.mark.asyncio
async def test_encrypt(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a. Encrypt (salt and hash) the plain_text password
    payload = test_data_login['encrypt']['payload']
    payload['encrypted_text'] = await try_encrypt(async_client, payload)
    # b Decrypt the encrypted text and compare with the input plain text
    response = await async_client.post('encrypt/verify/', json=payload)
    #  - Validate Response (200, 'Password is valid.')
    check_response(response)


@pytest.mark.asyncio
async def test_encrypt_fail(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a. Get valid encrypted text
    payload = test_data_login['encrypt']['payload']
    payload['encrypted_text'] = await try_encrypt(async_client, payload)
    # b. Change plain text to invalid password
    await try_fail_decrypt(async_client, payload, test_data_login, 'payload-1')
    # c. Change plain text to empty password
    await try_fail_decrypt(async_client, payload, test_data_login, 'payload-2', expected_status=422)


async def try_encrypt(async_client, payload):
    # a. Encrypt (salt and hash) the plain_text password
    response = await async_client.post('encrypt/', json=payload)
    # b. Validate response
    assert response.status_code == 200
    response_payload = response.json() or {}
    encrypted_text = response_payload.get('encrypted_text')
    assert encrypted_text is not None
    return encrypted_text


async def try_fail_decrypt(
        async_client, payload, payload_fail, test_case, expected_status=status.HTTP_401_UNAUTHORIZED):
    payload['plain_text'] = payload_fail['encrypt_fail'][test_case]['plain_text']
    # - Decrypt the encrypted text and compare with the input plain text
    response = await async_client.post('encrypt/verify/', json=payload)
    #  - Validate status (401)')
    check_response(response, expected_status=expected_status)
