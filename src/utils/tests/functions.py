from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from fastapi import Response

from src.domains.login.functions import map_user
from src.domains.user.models import User
from src.utils.db import crud
from src.utils.functions import get_otp_expiration
from src.utils.security.crypto import get_hashed_password
from src.utils.tests.constants import *


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


"""
Post check functions
"""


async def post_check(
        breadcrumbs, expected_result, client, db, fixture, expected_http_status=None, seqno=0) -> Response:
    """ Precondition: JSON fixtures are defined by route, followed by 'success' or 'fail'. """
    if not expected_http_status:
        expected_http_status = status.HTTP_200_OK if expected_result == SUCCESS else status.HTTP_401_UNAUTHORIZED

    payload = f'{PAYLOAD}-{seqno}' if seqno > 0 else PAYLOAD
    payload = await substitute(db, fixture.get(payload))
    response = await post_to_endpoint(
        client=client,
        breadcrumbs=breadcrumbs,
        fixture=payload
    )
    # a. Check response (model or exception)
    assert_response(
        response,
        expected_payload=fixture.get(f'{EXPECT}{seqno}'),
        expected_status=expected_http_status
    )
    # b. Check db attributes
    # Db can be checked only if the response is OK.
    # In case of an exception, the db record may have been updated but can not be retrieved here. Why?
    if get_model(response):
        await assert_db(db, fixture.get(f'{EXPECT_DB}{seqno}'))
    return response


async def assert_db(db, expected_payload):
    if not expected_payload:
        return

    expected_payload = await substitute(db, expected_payload)
    user = await crud.get_one_where(db, User, User.email, expected_payload['email'])
    # Assertions
    assert user.email == expected_payload['email']
    assert user.password == expected_payload['password']
    if expected_payload['otp'] == GT0:
        assert user.otp > 0
    else:
        assert user.otp == expected_payload['otp']
    if user.otp or expected_payload['password'] == STRING:
        validate_expiration(user.expired)
    if expected_payload['password'] != STRING:
        assert user.password is None
    assert user.fail_count == expected_payload['fail_count']
    assert user.status == expected_payload['status']


def validate_expiration(db_expiration, delta_seconds_allowed=10.0):
    """ Precondition: db_expiration has been set < 1 second ago. """
    assert db_expiration is not None
    now_expiration = get_otp_expiration()
    delta = now_expiration - db_expiration
    assert 0.0 < delta.total_seconds() < delta_seconds_allowed


async def post_to_endpoint(client, breadcrumbs, fixture):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    route = '/'.join(breadcrumbs)
    return await client.post(f'{route}/', json=fixture)


def get_leaf(fixture, breadcrumbs: list, expected_result):
    d = fixture
    for leaf in breadcrumbs:
        d = d.get(leaf, {})
    return d.get(expected_result, {})


async def substitute(db, fixture) -> dict:
    """ Substitute unpredictable attribute values from those in the db. """
    if fixture and any(v == GET_FROM_DB for v in fixture.values()):
        user = await get_user_from_db(db, fixture.get('email'))
        if user:
            fixture = {k: _try_substitute(k, v, user) for k, v in fixture.items()}
    return fixture


def _try_substitute(key, value, user):
    if value == GET_FROM_DB:
        if key == 'otp':
            value = user.otp
    return value


# async def add_otp_from_db(db, fixture):
#     # - First set the test-otp from the db, which has been set to an unpredictable value.
#     user = await get_user_from_db(db, fixture[PAYLOAD]['email'])
#     fixture[PAYLOAD]['otp'] = user.otp
#     return fixture


async def get_user_from_db(db, email):
    return await crud.get_one_where(db, User, User.email, email)


async def set_password_in_db(db, fixture, key):
    """ Encrypt password and put it in the db. """
    user = await get_user_from_db(db, fixture['email'])
    print(f'Old password to be hashed and set in db: {fixture[key]}')
    user.password = get_hashed_password(fixture[key])
    await crud.upd(db, User, user.id, map_user(user))
