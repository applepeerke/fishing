import csv
from src.utils.tests.constants import PAYLOAD, EXPECT_DB, EXPECT
from src.utils.tests.functions import create_nested_dict
from tests.tdd.TestCase import TestCase

NO_CHG = '*NC'


def get_tdd_test_scenarios(path) -> dict:
    """
    Retrieve JSON from fishing/tests/data/{domain}.csv
    Example:
    ------------------------------------------------------------------------------------------------------------------
    0            1   2         3       4                  5 6     7                  8       9   10 11      12
    Title	     TC  Endpoint  Entity  Input	     Repeat Expected response                UserStatus     Next
                                                            HTTP  Content            Message Pre Post
                                                            Status
    ------------------------------------------------------------------------------------------------------------------
    Registration 1   register  login   {"email": "d@s.c"} 0 422   *message           The ... 10 *NC		     -
    Registration 2   register  login   {"email": "d@s.c"} 0 422   *message	         The ... 20 *NC		     -
    Registration 3   register  login   {"email": "d@s.c"} 0 200   {"email": "d@s.c"}         NR 10 Inactive Send otp
    ------------------------------------------------------------------------------------------------------------------
    """
    rows = get_csv_rows(path)
    d = {}
    for row in rows:
        TC = TestCase(
            seqno=int(row[1]),
            endpoint=row[2],
            entity=row[3],
            payload=row[4],
            repetitions=int(row[5]),
            expected_response_http_status=row[6],
            expected_response_content=row[7],
            expected_response_message=row[8],
            user_status_pre=row[9],
            user_status_post=row[10],
            next_step=row[12],
            title=row[0]
        )
        # Payload fixture (maybe repeated)
        d1 = {}
        breadcrumbs = _get_breadcrumbs(TC, PAYLOAD)
        d0 = create_nested_dict(breadcrumbs, TC.payload)
        d1 = merge_dicts(d1, d0)

        # Expected response - model: User.UserStatus
        breadcrumbs = _get_breadcrumbs(TC, EXPECT_DB)
        expected_response = {'status': TC.user_status_pre if TC.user_status_post == NO_CHG else TC.user_status_post}
        d2 = create_nested_dict(breadcrumbs, expected_response)
        d1 = merge_dicts(d1, d2)
        # Expected response -Model or Exception
        if TC.expected_response_content:
            breadcrumbs = _get_breadcrumbs(TC, EXPECT)
            d2 = create_nested_dict(breadcrumbs, TC.expected_response_content)
            d1 = merge_dicts(d1, d2)
        # Merge dicts
        d = merge_dicts(d, d1)
    return d


def _get_breadcrumbs(tc: TestCase, leaf) -> list:
    # ID = seqno | precondition UserStatus | executions | expected HTTP status
    breadcrumbs = [f'{str(tc.seqno).zfill(3)}|{tc.user_status_pre}|{tc.executions}|{tc.expected_response_http_status}']
    breadcrumbs.extend([tc.entity, tc.endpoint, tc.expected_result, leaf])
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
