import json

from src.utils.tests.functions import get_csv_rows
from tests.tdd.CsvTestCase import CsvTestCase


def get_tdd_test_scenarios_scopes(path) -> list:
    """
    Retrieve JSON from fishing/tests/data/{domain}.csv
    """
    rows = get_csv_rows(path)
    test_cases = []
    for row in rows:
        d = {}
        if row[4]:
            r = json.dumps(row[4])
            d = json.loads(r)
        test_cases.append(CsvTestCase(
            title=row[0],
            seqno=int(row[1]),
            r1=row[2],
            r2=row[3],
            payload=d
        ))
    return test_cases
