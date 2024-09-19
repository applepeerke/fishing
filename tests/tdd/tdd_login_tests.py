import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.tests.functions import initialize_user_from_fixture, post_check


@pytest.mark.asyncio
async def test_login_TDD(test_tdd_scenarios_login: dict, client: AsyncClient, db: AsyncSession):
    """
    TDD
    All test scenarios via csv file 'tests/tdd/automatic_tests_login.csv'.
    JSON fixtures are created dynamically via csv rows, not via .json files.
    """
    kwargs = {'test_tdd_scenarios_login': test_tdd_scenarios_login, 'client': client, 'db': db}
    for Id, test_scenario in test_tdd_scenarios_login.items():
        for (r1, r2s) in test_scenario.items():
            for r2, r3s in r2s.items():
                for r3, results in r3s.items():
                    for result, fixture in results.items():
                        await run_test(Id, r1, r2, r3, result, **kwargs)


async def run_test(Id, r1, r2, r3, result, **kwargs):
    # Parameters
    db = kwargs['db']
    client = kwargs['client']
    fixture = kwargs['test_tdd_scenarios_login']
    # Breadcrumbs
    fixture_route = [Id, r1, r2, r3]
    api_route = [i for i in fixture_route if i]
    # CSV columns
    names = Id.split('|')  # seqno | precondition_userStatus | repeat | expected HTTP status
    target_user_status = None if names[1] == 'NR' else int(names[1])
    headers = {}

    # Optionally insert User record with desired UserStatus
    await initialize_user_from_fixture(fixture_route, result, db, fixture, target_user_status)
    executions = int(names[2])
    for exec_no in range(1, executions + 1):
        await post_check(
            api_route, fixture, int(names[3]), client, db, headers, fixture_route, route_from_index=1,
            check_response=exec_no == executions)
        print(f'* Test "{api_route[0]}" route "{' '.join(api_route[1:])}" was successful.')
