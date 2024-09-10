from fastapi.exceptions import ResponseValidationError
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import EMAIL, PASSWORD, LOGIN
from src.utils.tests.constants import SUCCESS, PAYLOAD
from src.utils.tests.functions import insert_record, assert_response, get_json
from src.utils.tests.virtual_hacker import tamper_items
from tests.functions import login_user, get_authorization_header


class CrudTest:
    def __init__(self, async_client: AsyncClient,
                 async_session: AsyncSession,
                 test_data: dict,
                 domain_url: str = None,
                 model=None,
                 login: bool = True):
        self._async_client = async_client
        self._async_session = async_session
        self._test_data = test_data
        self._domain_url = domain_url
        self._model = model
        self._login = login
        self._headers = None

    async def create(self):
        await self._preconditions()

        payload = self._test_data["create"]["payload"]
        expect = self._test_data["create"]["expect"]
        response = await self._async_client.post(f"{self._domain_url}/", json=payload, headers=self._headers)
        assert_response(response, expect, 200)
        got = response.json()
        response = await self._async_client.get(f"{self._domain_url}/{got['id']}", headers=self._headers)
        assert_response(response, expect, 200)

    async def read(self):
        await self._preconditions(self._test_data["initial_data"], ["payload"])
    
        payload = self._test_data["initial_data"]["payload"]
        expect = self._test_data["read"]["expect"]
        response = await self._async_client.get(f"{self._domain_url}/{payload['id']}", headers=self._headers)
        assert_response(response, expect, 200)
    
    async def update(self):
        await self._preconditions(self._test_data["initial_data"], ["payload"])
    
        initial_payload = self._test_data["initial_data"]["payload"]
        expect = self._test_data["update"]["expect"]
        payload = self._test_data["update"]["payload"]
        url = f"{self._domain_url}/{initial_payload['id']}"
        # Update
        response = await self._async_client.put(url, json=payload, headers=self._headers)
        assert_response(response, expect, 200)
    
        # Test input validation - virtual hacking
        await tamper_items(self._async_client, url, payload, headers=self._headers)

    async def delete(self):
        await self._preconditions(self._test_data["initial_data"], ["payload"])
    
        initial_payload = self._test_data["initial_data"]["payload"]
        expect = self._test_data["delete"]["expect"]
        url = f"{self._domain_url}/{initial_payload['id']}"
        # delete
        response = await self._async_client.delete(url, headers=self._headers)
        assert_response(response, expect, 200)
        # fetch - should raise
        try:
            response = await self._async_client.get(url, headers=self._headers)
            assert_response(response, None, 200)
        except ResponseValidationError:
            pass

    async def _preconditions(self, initial_data=None, fixtures=None):
        """ Set preconditions for tests. Injects directly in the db, ignoring api. """
        if self._login:
            test_data_login = get_json(LOGIN)
            payload = test_data_login[LOGIN][SUCCESS][PAYLOAD]
            response = await login_user(payload[EMAIL], payload[PASSWORD], self._async_session, self._async_client)
            self._headers = get_authorization_header(response)

        if fixtures:
            for key in fixtures:
                await insert_record(self._async_session, self._model, initial_data[key])
