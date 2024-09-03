import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.tests.constants import SUCCESS, FAIL, PAYLOAD
from src.utils.tests.functions import post_check, get_model, set_leaf


@pytest.mark.asyncio
async def test_encrypt(async_client: AsyncClient, async_session: AsyncSession, test_data_encrypt: dict):
    kwargs = {'client': async_client, 'db': async_session, 'fixture': test_data_encrypt}
    # Success
    # a. Calculate encryption and add it to payload
    api_route = ['encrypt']
    encrypted_text = await get_encrypted_text(api_route, **kwargs)
    # b. Add encrypted_text to payload
    api_route = ['encrypt', 'verify']
    test_data_encrypt = set_leaf(test_data_encrypt, api_route, SUCCESS, PAYLOAD, 'encrypted_text', encrypted_text)
    # c Decrypt the encrypted text and compare with the input plain text
    await post_check(api_route, 200, **kwargs)

    # Fail
    # a. Change plain text to invalid password
    await post_check(api_route, 401, async_client, async_session, test_data_encrypt, seq_no=1)
    # b. Change plain text to empty password
    await post_check(
        api_route, 422, async_client, async_session, test_data_encrypt, seq_no=2)


async def get_encrypted_text(api_route, client, db, fixture):
    # a. Encrypt (salt and hash) the plain_text password
    response = await post_check(api_route, 200, client, db, fixture)
    response_payload = get_model(response)
    return response_payload.get('encrypted_text')
