from fastapi.exceptions import ResponseValidationError
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import ID, EMAIL, ROLE_NAMES
from src.services.test.functions import login_with_fake_admin
from src.utils.tests.constants import PAYLOAD, EXPECT, INITIAL_DATA, SUCCESS, LOGIN, PASSWORD
from src.utils.tests.functions import insert_record, assert_response, get_json
from src.utils.tests.virtual_hacker import tamper_items


class CrudTest:
    def __init__(self, async_client: AsyncClient,
                 async_session: AsyncSession,
                 test_data: dict,
                 domain_url: str = None,
                 model=None,
                 login: bool = True):
        self._client = async_client
        self._db = async_session
        self._test_data = test_data
        self._domain_url = domain_url
        self._model = model
        self._login = login
        self._headers = None

    async def create(self):
        await self._preconditions()

        payload = self._test_data["create"][PAYLOAD]
        expect = self._test_data["create"][EXPECT]
        response = await self._client.post(f"{self._domain_url}/", json=payload, headers=self._headers)
        assert_response(response, expect, 200)
        got = response.json()
        response = await self._client.get(f"{self._domain_url}/{got[ID]}", headers=self._headers)
        assert_response(response, expect, 200)

    async def read(self):
        await self._preconditions(self._test_data[INITIAL_DATA])
    
        payload = self._test_data[INITIAL_DATA][PAYLOAD]
        expect = self._test_data["read"][EXPECT]
        response = await self._client.get(f"{self._domain_url}/{payload[ID]}", headers=self._headers)
        assert_response(response, expect, 200)
    
    async def update(self):
        await self._preconditions(self._test_data[INITIAL_DATA])
    
        initial_payload = self._test_data[INITIAL_DATA][PAYLOAD]
        expect = self._test_data["update"][EXPECT]
        payload = self._test_data["update"][PAYLOAD]
        Id = payload.get(ID, initial_payload[ID])
        url = f"{self._domain_url}/{Id}"
        # Update
        response = await self._client.put(url, json=payload, headers=self._headers)
        assert_response(response, expect, 200)
    
        # Test input validation - virtual hacking
        await tamper_items(self._client, url, payload, headers=self._headers)

    async def delete(self):
        await self._preconditions(self._test_data[INITIAL_DATA])
    
        initial_payload = self._test_data[INITIAL_DATA][PAYLOAD]
        expect = self._test_data["delete"][EXPECT]
        url = f"{self._domain_url}/{initial_payload[ID]}"
        # delete
        response = await self._client.delete(url, headers=self._headers)
        assert_response(response, expect, 200)
        # fetch - should raise
        try:
            response = await self._client.get(url, headers=self._headers)
            assert_response(response, None, 422)
        except ResponseValidationError:
            pass

    async def _preconditions(self, initial_data=None):
        """ Set preconditions for tests. After every test pytest has cleared the db. """
        if self._login:
            test_data_login = get_json(LOGIN)
            payload = test_data_login[LOGIN][SUCCESS][PAYLOAD]

            # Create a logged-in user from the json payload, with a fake role.
            response = await login_with_fake_admin(
                db=self._db,
                email=payload[EMAIL],
                password=payload[PASSWORD],
                role_names=payload[ROLE_NAMES]
            )

            # Add te authorization headers.
            self._headers = response.headers

        # Create an initial entity record.
        if initial_data:
            [await insert_record(self._db, self._model, initial_data[key])
             for key in initial_data if key.startswith(PAYLOAD)]
