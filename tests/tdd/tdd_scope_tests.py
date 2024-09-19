import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.acl.models import ACL
from src.domains.role.models import Role
from src.domains.scope.models import Scope
from src.domains.scope.scope_manager import ScopeManager
from src.domains.user.models import User
from tests.tdd.CsvTestCase import CsvTestCase


@pytest.mark.asyncio
async def test_scope_TDD(test_tdd_scenarios_scopes: list, client: AsyncClient, db: AsyncSession):
    """
    TDD
    All test scenarios via csv file 'tests/tdd/automatic_tests_scopes.csv'.
    JSON fixtures are created dynamically via csv rows, not via .json files.

    Assumption: Role has 1 ACL. The ACL contains all needed scopes (permissions).
    """
    # a. In db, from the single-acl TC's create all unique roles/acls and all acl-scopes detected in the csv.
    user = await _create_db(test_tdd_scenarios_scopes, db)
    # b. Test per multi-acl TC's if the resulting merged scopes are as expected.
    for TC in test_tdd_scenarios_scopes:
        if ',' not in TC.r1:
            continue  # Select multi roles/acls
        # Get the roles/acls from db.
        roles = [await crud.get_one_where(db, Role, Role.name, name.strip()) for name in TC.r1.split(',')]
        user.roles = roles
        await db.commit()

        # Get compressed scope_names from db (for all user roles)
        scope_manager = ScopeManager(db, user.email)
        scope_names_db = await scope_manager.get_user_scopes()
        # Get all scope names present in payload
        scope_names_expected = {scope_name for scope_name in get_scope_names_from_payload(TC)}
        # Check
        missing_in_db = {scope_name for scope_name in scope_names_expected if scope_name not in scope_names_db}
        missing_in_payload = {scope_name for scope_name in scope_names_db if scope_name not in scope_names_expected}
        assert not missing_in_db and not missing_in_payload
        # Success
        print(f'* Test {TC.seqno} "{TC.title}" for scopes was successful.')


async def _create_db(test_tdd_scenarios_scopes: [CsvTestCase], db: AsyncSession) -> User:
    """ Create the db with a user, roles, acls end scopes. The acls and scopes are not yet linked to the user. """
    email = 'scope_tests_tdd_user@example.com'
    user = await crud.add(db, User(email=email))
    # In db, create all scopes detected in the csv. They are the base.
    # - Add all unique scopes found.
    for TC in test_tdd_scenarios_scopes:
        # Select single acls
        if ',' in TC.r1:
            continue
        # Add not existing scope.
        for scope_name in get_scope_names_from_payload(TC):
            if not await crud.get_one_where(db, Scope, Scope.scope_name, scope_name):
                names = scope_name.split('_')
                await crud.add(db, Scope(entity=names[0], access=names[1]))

    # - Add all roles/acls.
    for TC in test_tdd_scenarios_scopes:
        # Select single roles/acls
        if ',' in TC.r1 or not TC.r2:
            continue
        # Add Role
        role = await crud.add(db, Role(name=TC.r1))
        # Add ACL
        acl = await crud.add(db, ACL(name=TC.r2))
        acl.roles.append(role)
        await db.commit()
        # Add ACL-scopes
        for scope_name in get_scope_names_from_payload(TC):
            scope = await crud.get_one_where(db, Scope, Scope.scope_name, scope_name)
            acl.scopes.append(scope)
            await db.commit()
    return user


def get_scope_names_from_payload(TC):
    payload = json.loads(TC.payload)
    return [f'{entity}_{access}' for entity, accesses in payload.get('entity', {}).items() for access in accesses]
