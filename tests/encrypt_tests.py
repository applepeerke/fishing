import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.tests.constants import SUCCESS, FAIL, PAYLOAD
from src.utils.tests.functions import post_check, get_model, set_leaf


@pytest.mark.asyncio
async def test_encrypt(client: AsyncClient, db: AsyncSession, test_data_encrypt: dict):
    kwargs = {'client': client, 'db': db}
    fixture = test_data_encrypt
    # Success
    # a. Calculate encryption and add it to payload
    api_route = ['encrypt']
    encrypted_text = await get_encrypted_text(api_route, fixture, **kwargs)
    # b. Add encrypted_text to payload
    api_route = ['encrypt', 'verify']
    #   Update fixture
    fixture = set_leaf(fixture, api_route, SUCCESS, PAYLOAD, 'encrypted_text', encrypted_text)
    # c Decrypt the encrypted text and compare with the input plain text
    await post_check(api_route, fixture, 200, **kwargs)

    # Fail
    # a. Change plain text to invalid password
    await post_check(api_route, fixture, 401,  seq_no=1, **kwargs)
    # b. Change plain text to empty password
    await post_check(
        api_route, fixture, 422, seq_no=2, **kwargs)


async def get_encrypted_text(api_route, fixture, client, db):
    # a. Encrypt (salt and hash) the plain_text password
    response = await post_check(api_route, fixture, 200, client, db)
    response_payload = get_model(response)
    return response_payload.get('encrypted_text')
