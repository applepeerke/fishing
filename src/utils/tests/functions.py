import csv
import datetime
import json
import os
from json import JSONDecodeError
from uuid import UUID

from fastapi import Response, HTTPException
from httpx import AsyncClient, ASGITransport
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.constants import AUTHORIZATION, X_REFRESH_TOKEN
from src.db import crud
from src.domains.login.user.functions import set_user_status_related_attributes
from src.domains.login.user.models import User, UserStatus
from src.utils.functions import get_otp_expiration, get_password_expiration, find_filename_path, get_pk
from src.utils.logging.log import logger
from src.utils.security.crypto import get_random_password, get_salted_hash
from src.utils.security.crypto import verify_hash
from src.utils.tests.constants import *
from src.utils.tests.constants import PAYLOAD


def has_authorization_header(response):
    return any(header in (AUTHORIZATION, X_REFRESH_TOKEN) for header in response.headers)


async def initialize_user_from_fixture(api_route, expected_status, db, fixture, user_status: int | None):
    """ Update UserStatus or add or delete a user """
    fixture = get_leaf(fixture, api_route, expected_status)
    plain_text_password = fixture.get(PAYLOAD, {}).get('password')
    if plain_text_password and 'right' not in plain_text_password.lower():
        plain_text_password = None
    await _initialize_user(db, get_pk(fixture, 'email'), user_status, plain_text_password)


async def _initialize_user(db, pk, target_status: int | None, plain_text_password=None) -> User | None:
    """ Initialize user from a target UserStatus. """
    if not pk:
        return
    user_old = await crud.get_one_where(db, User, att_name=User.email, att_value=pk)
    # a. Delete user (if no target status)
    if user_old and target_status is None:
        await crud.delete(db, User, user_old.id)
        return
    # b. Set attributes
    # - Status related attributes
    user = set_user_status_related_attributes(User(email=pk, fail_count=0), target_status)
    # - Password
    if not plain_text_password and target_status > 10:
        plain_text_password = get_random_password()
    user.password = get_salted_hash(plain_text_password)
    if target_status == UserStatus.Expired:
        user.password_expiration = datetime.datetime.now(datetime.timezone.utc)
    # c. Updert user
    if user_old:
        user.id = user_old.id
        return await crud.upd(db, User, user)
    else:
        return await crud.add(db, user)


def get_json(domain) -> dict:
    """ Retrieve JSON from fishing/tests/data/{subdir}/{domain}.json"""
    path = get_fixture_path(domain, 'json')
    with open(path, "r") as file:
        data = json.loads(file.read())
    return data


def get_fixture_path(domain, ext, automatic_tests=False) -> str:
    file_name = f'automatic_tests_{domain}.{ext}' if automatic_tests else f'{domain}.{ext}'
    return find_filename_path(file_name)


async def insert_record(db: AsyncSession, entity, payload: dict):
    statement = insert(entity).values(payload)
    await db.execute(statement=statement)
    await db.commit()


def assert_response(response, expected_payload=None, expected_status=status.HTTP_200_OK):
    if not response:
        if expected_status != status.HTTP_200_OK:
            assert not expected_payload
        return

    # Check response status
    # - Status in the expected payload has priority.
    if not expected_payload:
        expected_payload = {}
    expected_status = expected_payload.get(STATUS_CODE, expected_status)
    assert response.status_code == expected_status

    response_model = get_model(response)
    if response_model:
        # Check response model (except when all OK and no model asked to check)
        if (not expected_payload and response.status_code == expected_status
                and response.status_code == status.HTTP_200_OK):
            expected_payload = {}
        else:
            assert expected_payload
        assert_model_items(expected_payload, response_model)
    else:
        # Check response message
        response_message = get_message_from_response(response)
        if response_message:
            assert expected_payload
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
        # Ignore substitution vars
        if str(expected_value).startswith('*'):
            continue
        # Both object value (like UUID) to string and json value (like int) to string[[
        assert to_string(response_value) == to_string(expected_value)


def assert_message_items(expected: dict, response_message: dict):
    """ Precondition: All expected items exist in the response model. """
    for k, v in expected.items():
        if k == STATUS_CODE:  # status_code is a separate Response attribute
            continue
        assert response_message[k] == v


def get_message_from_response(response) -> dict:
    """
    response example-1: {'type': 'missing', 'loc':['body', 'new_password'],... }
    response example-2: {'detail: 'The user already exists.'}
    """
    if response.headers.get("Content-Type") != "application/json":
        if response.text and isinstance(response.text, str):
            return {'message': response.text}
        return {}
    message = response.json() or {}
    text = message.get(DETAIL, {})
    if not text:
        return {}
    # Repeating responses
    elif isinstance(text, list):
        return text[0]
    else:
        return message


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
GET check
"""


async def get_check(api_route, client: AsyncClient, expected_http_status=200, headers=None, params=None):
    try:
        response = await get_from_endpoint(client=client, api_route=api_route, params=params, headers=headers)
        assert response.status_code == expected_http_status
    except HTTPException as e:
        assert e.status_code == expected_http_status


"""
POST check functions
"""


async def post_check(
        api_route,
        fixture,
        expected_http_status,
        client: AsyncClient,
        db: AsyncSession,
        headers=None,
        fixture_route=None,
        check_response=True,
        route_from_index=0,
        seq_no=0,
) -> Response:
    """
    JSON fixture is defined by route, followed by 'success' or 'fail'.
    It contains  sub-fixtures like 'payload', 'expect' and 'expect-db'.
    """
    if not fixture_route:
        fixture_route = api_route
    expected_result = SUCCESS if expected_http_status == status.HTTP_200_OK else FAIL
    # Get payload (input) from tdd or from json leaf
    json_leaf = get_leaf(fixture, fixture_route, expected_result)
    payload_name = PAYLOAD if seq_no == 0 else f'{PAYLOAD}-{seq_no}'
    payload = await substitute(db, json_leaf.get(payload_name))
    response = await post_to_endpoint(
        client=client,
        api_route=api_route[route_from_index:],
        json_fixture=payload,
        headers=headers
    )
    # Last execution:
    if check_response:
        # a. Check response (model or exception)
        expected_payload_name = EXPECT if seq_no == 0 else f'{EXPECT}-{seq_no}'
        expected_payload = json_leaf.get(expected_payload_name)
        assert_response(
            response,
            expected_payload=expected_payload,
            expected_status=expected_http_status
        )
        # b. Check db attributes
        # Db can be checked only if the response is OK.
        # In case of an exception, the db record may have been updated but can not be retrieved here. Why?
        if get_model(response):
            await assert_db(db, expected_payload)
    return response


async def assert_db(db, expected_payload, pk='email'):
    # If response is an Authentication token it is not a db model
    if not expected_payload or pk not in expected_payload:
        return

    expected_payload = await substitute(db, expected_payload)
    user = await crud.get_one_where(db, User, User.email, expected_payload[pk])
    # Assertions
    assert user.email == expected_payload[pk]
    if PASSWORD in expected_payload:
        if expected_payload[PASSWORD] is None:
            assert user.password is None
            assert user.password_expiration is None
        else:
            assert verify_hash(expected_payload[PASSWORD], user.password)
            if 'expiration' in expected_payload:
                validate_expiration(user.password_expiration, expiration_type=expected_payload['expiration'])
    if 'fail_count' in expected_payload:
        assert user.fail_count == expected_payload['fail_count']
    if 'status' in expected_payload:
        assert user.status == expected_payload['status']


def validate_expiration(db_expiration, delta_seconds_allowed=10.0, expiration_type=SUBST_GET_PASSWORD_EXPIRY):
    """ Precondition: db_expiration has been set < 1 second ago. """
    assert db_expiration is not None
    now_expiration = get_otp_expiration() if expiration_type == SUBST_GET_OTP_EXPIRY else get_password_expiration()
    delta = now_expiration - db_expiration
    assert 0.0 < delta.total_seconds() < delta_seconds_allowed


async def get_from_endpoint(client: AsyncClient, api_route, params=None, headers=None):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    route = '/'.join(api_route)
    return await client.get(f'{route}/', params=params, headers=headers)


async def post_to_endpoint(client: AsyncClient, api_route, json_fixture, headers=None):
    """ Precondition: JSON fixtures are defined by endpoint name. """
    route = '/'.join(api_route)
    return await client.post(f'{route}/', json=json_fixture, headers=headers)


def get_leaf(fixture, breadcrumbs: list, expected_result, payload=None) -> dict:
    """
    Get a fixture (like a payload) from a fixture set.
    @fixture: E.g. "password / change / success / payload"
    @breadcrumbs:  E.g. "password / change"
    @expected_result: "success" or "fail"
    @payload: E.g.  "payload" or "expect"
    """
    d = fixture
    for leaf in breadcrumbs:
        d = d.get(leaf, {})
    leaf = d.get(expected_result, {})
    return leaf.get(payload, {}) if payload else leaf


def set_leaf(fixture, breadcrumbs, expected_result, leaf, key, value) -> dict:
    b = breadcrumbs.copy()
    b.extend([expected_result, leaf, key])
    # Add a value at a deep nested level
    add_to_nested_dict(fixture, b, value)
    return fixture


def add_to_nested_dict(d, keys, value) -> dict:
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value
    return d


def create_nested_dict(elements, value) -> dict:
    d = current = {}
    try:
        for i in range(len(elements)):
            element = elements[i]
            if element not in d:
                if i < len(elements) - 1:
                    d[element] = {}
                else:
                    # Assign the value to the last key
                    d[element] = value if isinstance(value, dict) else json.loads(value) if value else {}
                    break
            d = d[element]
    except JSONDecodeError as e:
        print(f'Error in "create_nested_dict": {e}')
        raise
    return current


async def substitute(db, fixture) -> dict:
    """ Substitute unpredictable attribute values from those in the db. """
    if fixture and any(v == SUBST_GET_FROM_DB for v in fixture.values()):
        user = await get_user_from_db(db, fixture.get('email'))
        if user:
            fixture = {k: _try_substitute(k, v, user) for k, v in fixture.items()}
    return fixture


def _try_substitute(key, value, user):
    if value == SUBST_GET_FROM_DB:
        if key == 'otp':
            value = user.otp
    return value


async def get_user_from_db(db, email):
    return await crud.get_one_where(db, User, User.email, email)


def merge_dicts(d1, d2):
    for key, value in d2.items():
        if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
            merge_dicts(d1[key], value)
        else:
            d1[key] = value
    return d1


def get_csv_rows(path=None, skip_rows=1):
    rows = _try_csv_rows(path, ',')
    if not rows or len(rows[0]) == 1:
        rows = _try_csv_rows(path, ';')
    return rows[skip_rows:] if len(rows) > skip_rows else []


def _try_csv_rows(path, delimiter) -> list:
    with open(path, encoding='utf-8-sig', errors='replace') as csvFile:
        csv_reader = csv.reader(
            csvFile, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
        return [row for row in csv_reader if row[0]]
