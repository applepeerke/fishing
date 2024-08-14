import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.utils.tests.functions import check_response


@pytest.mark.asyncio
async def test_encrypt(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a. Encrypt (salt and hash) the plain_text password
    payload = test_data_login["encrypt"]["payload"]
    payload['encrypted_text'] = await try_encrypt(async_client, payload)
    # b Decrypt the encrypted text and compare with the input plain text
    response = await async_client.post("validate/", json=payload)
    #  - Validate StatusResponse (200, "Password is valid.")
    expected = test_data_login["encrypt"]["expect"]
    check_response(response, expected)


@pytest.mark.asyncio
async def test_encrypt_fail(async_client: AsyncClient, async_session: AsyncSession, test_data_login: dict):
    # a. Get valid encrypted text
    payload = test_data_login["encrypt"]["payload"]
    payload['encrypted_text'] = await try_encrypt(async_client, payload)
    # b. Change plain text to invalid password
    await try_fail_decrypt(async_client, payload, test_data_login, "payload-1")
    # c. Change plain text to empty password
    await try_fail_decrypt(async_client, payload, test_data_login, "payload-2")


async def try_encrypt(async_client, payload):
    # a. Encrypt (salt and hash) the plain_text password
    response = await async_client.post("password/", json=payload)
    # b. Validate response
    assert response.status_code == 200
    response_payload = response.json() or {}
    encrypted_text = response_payload.get('encrypted_text')
    assert encrypted_text is not None
    return encrypted_text


async def try_fail_decrypt(async_client, payload, payload_fail, test_case, expected_status=status.HTTP_401_UNAUTHORIZED):
    payload['plain_text'] = payload_fail["encrypt_fail"][test_case]['plain_text']
    # - Decrypt the encrypted text and compare with the input plain text
    response = await async_client.post("validate/", json=payload)
    #  - Validate StatusResponse (403, "Password is not valid.")
    expected = payload_fail["encrypt_fail"]["expect"]
    check_response(response, expected, expected_status)
