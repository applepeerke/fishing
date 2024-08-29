import csv
from src.utils.tests.constants import PAYLOAD, EXPECT_DB, EXPECT
from src.utils.tests.functions import create_nested_dict


def get_tdd_test_scenarios(path) -> dict:
    """
    Retrieve JSON from fishing/tests/data/{domain}.csv
    Example:
    ------------------------------------------------------------------------------------------------------------------
    0            1    2    3      4        5        6                  7 8    9                  10  11     12
    Title	     TC  Pre  Entity Endpoint  Expected Input	      Repeat Exp. Exp.               Exp.       Next
                     Sts                   Result                        HTTP Response           Status
    ------------------------------------------------------------------------------------------------------------------
    Registration 1   10	 login	register   fail	    {"email": "d@s.c"} 0  422 {"detail": ...}    *NC		     -
    Registration 2   20	 login	register   fail	    {"email": "d@s.c"} 0  422 {"detail": ...}	 *NC		     -
    Registration 3   NR	 login	register   success	{"email": "d@s.c"} 0  200 {"email": "d@s.c"} 10 Inactive Send otp
    ------------------------------------------------------------------------------------------------------------------
    """
    rows = get_csv_rows(path)

    d = {}
    for row in rows:
        # Payload fixture (maybe repeated)
        d1 = {}
        executions = int(row[7]) + 1
        breadcrumbs = _get_breadcrumbs(row, PAYLOAD, executions)
        d0 = create_nested_dict(breadcrumbs, row[6])
        d1 = merge_dicts(d1, d0)

        # Expected response - model: User.UserStatus
        breadcrumbs = _get_breadcrumbs(row, EXPECT_DB, executions)
        expected_response = {'status': int(row[2]) if row[10] == '*NC' else int(row[10])}
        d2 = create_nested_dict(breadcrumbs, expected_response)
        d1 = merge_dicts(d1, d2)
        # Expected response - message: Exception
        if row[9]:  # Model or Exception
            breadcrumbs = _get_breadcrumbs(row, EXPECT, executions)
            d2 = create_nested_dict(breadcrumbs, row[9])
            d1 = merge_dicts(d1, d2)
        # Merge dicts
        d = merge_dicts(d, d1)
    return d


def _get_breadcrumbs(row, leaf, executions=1) -> list:
    # ID = seqno | precondition UserStatus | executions | expected HTTP status
    breadcrumbs = [f'{row[1].zfill(3)}|{row[2]}|{executions}|{row[8]}']
    breadcrumbs.extend(row[3:6])
    breadcrumbs.append(leaf)
    return breadcrumbs


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
