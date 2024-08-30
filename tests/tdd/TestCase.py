from starlette import status
from src.utils.tests.constants import SUCCESS, FAIL, SUBST_MESSAGE, DETAIL


class TestCase:
    @property
    def seqno(self):
        return self._seqno

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def entity(self):
        return self._entity

    @property
    def payload(self):
        return self._payload

    @property
    def executions(self):
        return self._executions

    @property
    def expected_result(self):  # success or fail
        return self._expected_result

    @property
    def expected_response_http_status(self):
        return self._expected_response_http_status

    @property
    def expected_response_content(self):
        return self._expected_response_content

    @property
    def expected_response_message(self):
        return self._expected_response_message

    @property
    def user_status_pre(self):
        return self._user_status_pre

    @property
    def user_status_post(self):
        return self._user_status_post

    @property
    def next_step(self):
        return self._title

    @property
    def title (self):
        return self._title

    def __init__(self,
                 seqno,
                 endpoint,
                 entity,
                 payload,
                 repetitions=0,
                 expected_response_http_status=status.HTTP_200_OK,
                 expected_response_content=None,
                 expected_response_message=None,
                 user_status_pre=0,
                 user_status_post=0,
                 next_step=None,
                 title=None):
        """
        @param seqno: Testcase number.
        @param endpoint: Last leaf of route.
        @param entity: Entity.
        @param payload: JSON payload.
        @param repetitions: Number of payload repetitions before expected response is checked.
        @param expected_response_http_status: HTTP status.
        @param expected_response_content: Response.text.
        @param expected_response_message: Message in Response.text.
        @param user_status_pre: Database User.status to be set before the test is executed.
        @param user_status_post: Database User.status to be checked after test.
        @param next_step: Expected next step to be executed.
        @param title: Title of this testcase
        """
        self._seqno: int = seqno
        self._endpoint: str = endpoint
        self._entity: str = entity
        self._payload: dict = payload
        self._repetitions: int = repetitions
        self._expected_response_http_status: int = expected_response_http_status
        self._expected_response_content: dict = expected_response_content
        self._expected_response_message: str = expected_response_message
        self._user_status_pre: int = user_status_pre
        self._user_status_post: int = user_status_post
        self._next_step: str = next_step
        self._title: str = title
        # Derived
        self._executions = self._repetitions + 1
        self._expected_result = SUCCESS if expected_response_http_status == status.HTTP_200_OK else FAIL
        # "*message" refers to the specified message
        if self._expected_response_content == SUBST_MESSAGE:
            self._expected_response_content = {DETAIL: self._expected_response_message}


