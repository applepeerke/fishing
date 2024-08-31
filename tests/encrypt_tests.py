import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.tests.constants import SUCCESS, FAIL, PAYLOAD
from src.utils.tests.functions import post_check, get_model, set_leaf


@pytest.mark.asyncio
async def test_encrypt(async_client: AsyncClient, async_session: AsyncSession, test_data_encrypt: dict):
    # Success
    # a. Calculate encryption and add it to payload
    breadcrumbs = ['encrypt']
    encrypted_text = await get_encrypted_text(breadcrumbs, async_client, async_session, test_data_encrypt)
    # b. Add encrypted_text to payload
    breadcrumbs = ['encrypt', 'verify']
    test_data_encrypt = set_leaf(test_data_encrypt, breadcrumbs, SUCCESS, PAYLOAD, 'encrypted_text', encrypted_text)
    # c Decrypt the encrypted text and compare with the input plain text
    await post_check(breadcrumbs, SUCCESS, async_client, async_session, test_data_encrypt)

    # Fail
    # a. Change plain text to invalid password
    await post_check(breadcrumbs, FAIL, async_client, async_session, test_data_encrypt, seq_no=1)
    # b. Change plain text to empty password
    await post_check(
        breadcrumbs, FAIL, async_client, async_session, test_data_encrypt, seq_no=2, expected_http_status=422)


async def get_encrypted_text(breadcrumbs, async_client, async_session, fixture):
    # a. Encrypt (salt and hash) the plain_text password
    response = await post_check(breadcrumbs, SUCCESS, async_client, async_session, fixture)
    response_payload = get_model(response)
    return response_payload.get('encrypted_text')
