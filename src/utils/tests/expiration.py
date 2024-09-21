import os

from starlette.responses import Response

from src.domains.login.token.constants import JWT_ACCESS_TOKEN_EXPIRY_SECONDS, JWT_REFRESH_TOKEN_EXPIRY_DAYS


class Expiration:
    @property
    def access_token_expiration_seconds(self):
        return self._access_token_expiration_seconds

    @property
    def refresh_token_expiration_days(self):
        return self._refresh_token_expiration_days

    def __init__(self, access_token_expiration_seconds=int | None, refresh_token_expiration_days=int | None):

        self._access_token_expiration_seconds = access_token_expiration_seconds
        self._refresh_token_expiration_days = refresh_token_expiration_days

        self._access_token_expiry_seconds_save = os.getenv(JWT_ACCESS_TOKEN_EXPIRY_SECONDS)
        self._refresh_token_expiry_days_save = os.getenv(JWT_REFRESH_TOKEN_EXPIRY_DAYS)

        self.set_access_token_expiration(access_token_expiration_seconds)
        self.set_refresh_token_expiration(refresh_token_expiration_days)

    @staticmethod
    def set_access_token_expiration(value):
        if isinstance(value, int):
            os.environ[JWT_ACCESS_TOKEN_EXPIRY_SECONDS] = str(value)

    @staticmethod
    def set_refresh_token_expiration(value):
        if isinstance(value, int):
            os.environ[JWT_REFRESH_TOKEN_EXPIRY_DAYS] = str(value)

    def reset_access_token_expiration(self):
        os.environ[JWT_ACCESS_TOKEN_EXPIRY_SECONDS] = self._access_token_expiry_seconds_save
        self._access_token_expiration_seconds = int(self._access_token_expiry_seconds_save)

    def reset_refresh_token_expiration(self):
        os.environ[JWT_REFRESH_TOKEN_EXPIRY_DAYS] = self._refresh_token_expiry_days_save
        self._refresh_token_expiration_days = int(self._refresh_token_expiry_days_save)


