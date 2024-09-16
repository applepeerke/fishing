from src.utils.tests.constants import PAYLOAD, EXPECT_DB, EXPECT, NO_CHG
from src.utils.tests.functions import create_nested_dict, get_csv_rows, merge_dicts
from tests.tdd.CsvTestCase import CsvTestCase


def get_tdd_test_scenarios_login(path) -> dict:
    """
    Retrieve JSON from fishing/tests/data/{domain}.csv
    Example:
    ------------------------------------------------------------------------------------------------------------------
    0            1   2         3       4      5                6    7  8                 9        10  11 12   13
    Title	     TC  __________Route_______   Input	           Repeat Expected response           UserStatus  Next
                     Group  Entity  Endpoint                    HTTP  Content            Message Pre Post
                                                               Status
    ------------------------------------------------------------------------------------------------------------------
    Registration 1   user  login  register   {"email": "d@s.c"} 0 422   *message           The ... 10 *NC		     -
    Registration 2   user  login  register   {"email": "d@s.c"} 0 422   *message	       The ... 20 *NC		     -
    Registration 3   user  login  register   {"email": "d@s.c"} 0 200   {"email": "d@s.c"}         NR 10 Inact. Send otp
    ------------------------------------------------------------------------------------------------------------------
    """
    rows = get_csv_rows(path)
    d = {}
    for row in rows:
        TC = CsvTestCase(
            title=row[0],
            seqno=int(row[1]),
            r1=row[2],
            r2=row[3],
            r3=row[4],
            payload=row[5],
            repetitions=int(row[6]),
            expected_response_http_status=int(row[7]),
            expected_response_content=row[8],
            expected_response_message=row[9],
            user_status_pre=row[10],
            user_status_post=row[11],
            next_step=row[13],
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


def _get_breadcrumbs(tc: CsvTestCase, leaf) -> list:
    """ The API route (last elements may be empty) """
    # ID = seqno | precondition UserStatus | executions | expected HTTP status
    breadcrumbs = [f'{str(tc.seqno).zfill(3)}|{tc.user_status_pre}|{tc.executions}|{tc.expected_response_http_status}']
    breadcrumbs.extend([tc.r1, tc.r2, tc.r3, tc.expected_result, leaf])
    return breadcrumbs
