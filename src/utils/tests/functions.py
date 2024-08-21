from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status


async def insert_record(async_session: AsyncSession, entity, payload: dict):
    statement = insert(entity).values(payload)
    await async_session.execute(statement=statement)
    await async_session.commit()


def check_response(response, expected_payload=None, expected_status=status.HTTP_200_OK):
    # After a delete None is returned and {} expected.
    if not response and not expected_payload:
        return
    assert response.status_code == expected_status
    # Only a status check
    if not expected_payload:
        return
    # Check model.
    if response.headers.get("Content-Type") == "application/json":
        response_payload = response.json() or {}
        check_items(expected_payload, response_payload)


def check_items(expected, response):
    for k, expected_value in expected.items():
        response_value = response[k]
        expected_value = ignore_secret(response_value, expected_value)
        # Both object value (like UUID) to string and json value (like int) to string[[
        assert to_string(response_value) == to_string(expected_value)


def ignore_secret(response_value, expected_value):
    """ Secrets are ignored in the comparison. """
    if isinstance(response_value, str) and all(i == '*' for i in response_value):
        return response_value
    return expected_value


def to_string(value):
    return str(value) \
        if isinstance(value, UUID) or isinstance(value, int) \
        else value


