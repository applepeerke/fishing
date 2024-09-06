import os

from fastapi.exceptions import ResponseValidationError
from httpx import AsyncClient

max_len_attributes = set()

LONG_STRING = 'a' * 1025
LONG_INT = int('1' * 33)
BLANK = ' '
EMPTY = ''


async def tamper_items(async_client: AsyncClient, url, payload, headers):
    global max_len_attributes
    if not max_len_attributes:
        max_len_attributes = find_max_length_attributes()
    for k, value in payload.items():
        # "id" is an internal attribute and not exposed, and may return 200 instead of 422.
        if k == 'id':
            continue
        # a. String
        if isinstance(value, str):
            if k not in max_len_attributes:
                # Test overflow. N.B. Allow text like notes to be long.
                await _tamper_item(async_client, url, payload, k, LONG_STRING, headers)
            # Test content. Invalid character "<" should not be allowed in any string.
            await _tamper_item(async_client, url, payload, k, '<', headers)
        # b. Int or bool
        elif isinstance(value, int):
            await _tamper_item(async_client, url, payload, k, LONG_INT, headers)


async def _tamper_item(async_client: AsyncClient, url, payload, key, value, headers=None):
    value_save = payload[key]
    payload[key] = value  # Save
    try:
        response = await async_client.put(url, json=payload, headers=headers)
        # OK: Status 422 from pydantic @model_validator.
        assert response.status_code == 422
    except ResponseValidationError:
        # OK: FastAPI validation error. E.g. from "max_len" or a regex in "schema_extra" directly in the attribute.
        pass
    finally:
        payload[key] = value_save  # Restore


def find_max_length_attributes() -> set:
    atts = set()
    for path in _find_model_filenames():
        with open(path) as file:
            for line in file:
                # Remember last attribute (line may be wrapped)
                p = line.find(':')
                if p > -1:
                    value = line[:p].strip()
                    # Valid attribute name?
                    if BLANK not in value:
                        att = value
                if 'max_length' in line and att:
                    atts.add(att)
                    att = EMPTY
    return atts


def _find_model_filenames():
    """
    Return all file paths matching the specified file type in the specified base directory (recursively).
    """
    app_root = os.getenv("APP_ROOT")
    app_root_tests = os.getenv("APP_ROOT_TESTS")
    walk_path = os.path.abspath(os.curdir)
    # If called from tests (pytest), substitute basename.
    if os.path.basename(walk_path) == app_root_tests:
        walk_path = walk_path.rstrip(app_root_tests)
        walk_path = f'{walk_path}{app_root}'
    # If called from a subdir, go back to app root
    elif app_root in walk_path and walk_path.count(app_root) == 1:
        p = walk_path.find(app_root) + len(app_root)
        walk_path = walk_path[:p]
    # Walk from app root
    for path, dirs, files in os.walk(walk_path):
        for filename in files:
            if filename == 'models.py':
                yield os.path.join(path, filename)
