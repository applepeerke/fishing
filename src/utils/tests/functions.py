from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from tests.data.constants import STATUS_CODE


async def insert_record(async_session: AsyncSession, entity, payload: dict):
    statement = insert(entity).values(payload)
    await async_session.execute(statement=statement)
    await async_session.commit()


def assert_response(response, expected_payload=None, expected_status=status.HTTP_200_OK):
    if not response or not isinstance(expected_payload, dict):
        return
    # Status in the expected payload has priority.
    expected_status = expected_payload.get(STATUS_CODE, expected_status)
    assert response.status_code == expected_status
    # Try to check returned model.
    response_model = get_model(response)
    if response_model:
        assert_model_items(expected_payload, response_model)
    else:
        response_message = get_message_from_response(response)
        assert_message_items(expected_payload, response_message)


def get_model(response) -> dict:
    if not response.headers.get("Content-Type") == "application/json":
        return {}
    response_payload = response.json() or {}
    # Error message: no further evaluation.
    return response_payload if response_payload and not response_payload.get('detail') \
        else {}


def assert_model_items(expected, response):
    """ Precondition: All expected items exist in the response model. """
    for k, expected_value in expected.items():
        if k == STATUS_CODE:  # status_code is a separate Response attribute
            continue
        response_value = response[k]
        expected_value = ignore_secret(response_value, expected_value)
        # Both object value (like UUID) to string and json value (like int) to string[[
        assert to_string(response_value) == to_string(expected_value)


def assert_message_items(expected: dict, response_message: dict):
    """ Precondition: All expected items exist in the response model. """
    for k, v in expected.items():
        if k == STATUS_CODE:  # status_code is a separate Response attribute
            continue
        assert response_message[k] == v


def get_message_from_response(response) -> dict:
    """ return example: {'type': 'missing', 'loc':['body', 'new_password'],... } """
    if response.headers.get("Content-Type") == "application/json":
        d = response.json() or {}
        text = d.get('detail', {})
        return {} if not text or not isinstance(text, list) else text[0]
    return {'message': response.text}


def ignore_secret(response_value, expected_value):
    """ Secrets are ignored in the comparison. """
    if isinstance(response_value, str) and all(i == '*' for i in response_value):
        return response_value
    return expected_value


def to_string(value):
    return str(value) \
        if isinstance(value, UUID) or isinstance(value, int) \
        else value


