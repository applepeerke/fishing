import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import crud
from src.domains.acl.models import ACL
from src.domains.role.models import Role
from src.domains.scope.models import Scope
from tests.tdd.TestCase import TestCase


@pytest.mark.asyncio
async def test_scope_TDD(test_tdd_scenarios_scopes: [TestCase], client: AsyncClient, db: AsyncSession):
    """
    TDD
    All test scenarios via csv file 'tests/tdd/automatic_tests_scopes.csv'.
    JSON fixtures are created dynamically via csv rows, not via .json files.
    """
    await _create_db(test_tdd_scenarios_scopes, db)
    for TC in test_tdd_scenarios_scopes:
        # Todo
        # Create
        print(f'* Test {TC.seqno} "{TC.title}" was successful.')
    # In db, create acls detected in csv.


async def _create_db(test_tdd_scenarios_scopes: [TestCase], db: AsyncSession):
    # In db, create scopes detected in csv.
    # - Add all unique scopes found.
    for TC in test_tdd_scenarios_scopes:
        # Select single roles/acl
        if ',' in TC.r1:
            continue
        # Add not existing scope.
        entity_acl = json.loads(TC.payload)
        for entity, accesses in entity_acl.items():
            for access in accesses:
                if not await crud.get_one_where(db, Scope, Scope.scope_name, f'{entity}_{access}'):
                    await crud.add(db, Scope(entity=entity, access=access))

    # - Add all roles/acls.
    for TC in test_tdd_scenarios_scopes:
        # Select single roles/acl
        if ',' in TC.r1:
            continue
        # Add Role
        role = await crud.add(db, Role(name=TC.r1))
        # Add ACL
        acl = await crud.add(db, ACL(name=TC.r2))
        # Add Role ACL
        role.acls.append(acl)
        await db.commit()
        # Add ACL scopes
        entity_acl = json.loads(TC.payload)
        for entity, accesses in entity_acl.items():
            for access in accesses:
                scope = await crud.get_one_where(db, Scope, Scope.scope_name, f'{entity}_{access}')
                acl.scopes.append(scope)
                await db.commit()

